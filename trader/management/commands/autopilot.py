import asyncio
import logging
import signal
import time
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from trader.aio.db import database_sync_to_async
from trader.aio.providers import XEtrade
from trader.models import AutoPilotTask, ProviderSession, ServiceProvider

# pylint: disable=invalid-name
logger = logging.getLogger("trader.autopilot")
PREFIX = "[autopilot]"


@database_sync_to_async
def get_passengers():
    return list(
        AutoPilotTask.objects.all()
        .select_related('provider', 'provider__broker', 'strategy', 'account', 'user')
        .filter(status=AutoPilotTask.CREATED)
    )


@database_sync_to_async
def get_config():
    return ServiceProvider.objects.get(id=1)


@database_sync_to_async
def get_token(config):
    config_session = ProviderSession.objects.filter(
        provider=config).first()
    if not config_session:
        return None
    return (config_session.access_token,
            config_session.access_token_secret)


@database_sync_to_async
def set_passenger_status(passenger: AutoPilotTask, status: int):
    passenger.status = status
    passenger.save(update_fields=['status'])


async def driver(name: str, queue: asyncio.Queue):
    logger.info("%s %s online.", PREFIX, name)
    try:
        pilot: AutoPilotTask = await queue.get()
        etrade: XEtrade = await get_provider(pilot)
        # TODO: implemente driver

        # for _ in range(3):
        #     print(f'{pilot.symbol + ":":<6} getting quote...')
        #     start = time.perf_counter()
        #     quote = await etrade.get_quote(pilot.symbol)
        #     elapsed = time.perf_counter() - start
        #     last_price = Decimal(str(quote.get("All").get("lastTrade")))
        #     print(f'{pilot.symbol + ":":<6} {last_price} {"":>20} {elapsed:0.2f} sec')
        #     print(f'{pilot.symbol + ":":<6} sleeping 1 sec')
        #     await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("%s %s stopping...", PREFIX, name)

    except Exception as exception:  # pylint: disable=broad-except
        logger.error("%s %s %s: %s", PREFIX, name,
                     type(exception).__name__,
                     str(exception), exc_info=1)
    finally:
        logger.info("%s %s done.", PREFIX, name)
        queue.task_done()


async def get_provider(pilot: AutoPilotTask):
    token, token_secret = (await get_token(pilot.provider)) or (None, None)
    return XEtrade(pilot.provider, token, token_secret)


async def shutdown(sig, loop):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info("%s received exit signal %s...", PREFIX, sig.name)
    logger.info("%s offboarding outstanding passengers.", PREFIX)
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    if len(tasks) > 0:
        logger.info("%s cancelling %s outstanding tasks.", PREFIX, len(tasks))
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("%s flushing metrics.", PREFIX)
    loop.stop()


def setup_graceful_shutdown():
    loop = asyncio.get_running_loop()
    signals = (signal.SIGHUP, signal.SIGTERM,
               signal.SIGQUIT, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop)))


async def main():
    logger.info("%s Starting...", PREFIX)
    setup_graceful_shutdown()

    logger.info("%s Enabled.", PREFIX)
    # Create a queue that we will use to store our "workload".
    queue = asyncio.Queue(maxsize=settings.AUTOPILOT_CAPACITY)

    while True:
        if queue.full():
            logger.debug("%s at capacity (%s).", PREFIX,
                         settings.AUTOPILOT_CAPACITY)
            await asyncio.sleep(1)
            continue

        logger.debug("%s looking for passengers...", PREFIX)
        passengers = await get_passengers()
        if not passengers:
            logger.debug("%s no passengers. sleeping for 1 sec.", PREFIX)
            await asyncio.sleep(1)
            continue

        logger.debug("%s %s passengers in line.", PREFIX, len(passengers))
        for passngr in passengers:
            await queue.put(passngr)
            await set_passenger_status(passngr, AutoPilotTask.QUEUED)
            asyncio.create_task(
                driver(f'driver-{passngr.user_id}-{passngr.symbol}', queue))
            if queue.full():
                break

        await asyncio.sleep(1)


class Command(BaseCommand):
    help = 'Follow positions and determine when to exit'

    def add_arguments(self, parser):
        # parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        try:
            asyncio.run(main())
        except asyncio.CancelledError:
            logger.info("%s cancelled.", PREFIX)
        finally:
            logger.info("%s successful sutdown!", PREFIX)
