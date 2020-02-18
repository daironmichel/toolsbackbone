import asyncio
import logging
import signal
import time
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from trader.aio.db import database_sync_to_async
from trader.aio.providers import AsyncEtrade
from trader.enums import MarketSession
from trader.models import AutoPilotTask, ProviderSession, ServiceProvider
from trader.utils import time_till_market_open

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
def get_stored_session(config):
    return ProviderSession.objects.filter(
        provider=config).first()


@database_sync_to_async
def delete_passenger(passenger: AutoPilotTask):
    passenger.delete()


@database_sync_to_async
def update_passenger(passenger: AutoPilotTask, fields: dict):
    updated_fields = []
    for field, value in fields.items():
        setattr(passenger, field, value)
        updated_fields.append(field)
    passenger.save(update_fields=updated_fields)


@database_sync_to_async
def refresh_passenger_signal(passenger: AutoPilotTask):
    # deleting model field will cause a refresh from db on get
    del passenger.signal
    return passenger.signal


async def get_provider(pilot: AutoPilotTask):
    stored_session = await get_stored_session(pilot.provider)
    return AsyncEtrade(pilot.provider, stored_session)


async def buy_position(pilot_name: str, passenger: AutoPilotTask):
    # get position
    # get quote
    # place order
    # watch order until executed or 5sec
    # cancel order if 5sec passed and no fill or partial
    # repeat untill out of position
    await asyncio.sleep(3)


async def sell_position(pilot_name: str, passenger: AutoPilotTask):
    # get position
    # get quote
    # place order
    # watch order until executed or 5sec
    # cancel order if 5sec passed and no fill or partial
    # repeat untill out of position
    await asyncio.sleep(3)


async def track_position(pilot_name: str, passenger: AutoPilotTask):
    # get position
    # get quote
    pass


async def green_light(pilot_name: str, passenger: AutoPilotTask,
                      etrade: AsyncEtrade) -> bool:
    # handle override signal
    if passenger.signal == AutoPilotTask.MANUAL_OVERRIDE:
        logger.info("%s %s received signal MANUAL_OVERRIDE.",
                    PREFIX, pilot_name)
        logger.info("%s %s releasing control...", PREFIX, pilot_name)
        await update_passenger(passenger, {'status': AutoPilotTask.DONE})
        return False

    # if no market session, sleep 1h (repeat until market opens)
    if MarketSession.current(passenger.is_otc) is None:
        logger.debug("%s %s market is closed. sleeping 1h",
                     PREFIX, pilot_name)
        time_till_open = time_till_market_open(passenger.is_otc)
        await asyncio.sleep(time_till_open)
        return False

    # if no access token, sleep 1s (repeat until valid access)
    if not etrade.is_session_active():
        logger.debug("%s %s waiting for valid %s session...",
                     PREFIX, pilot_name, etrade.name)
        await asyncio.sleep(1)
        return False

    return True


async def driver(name: str, queue: asyncio.Queue):
    logger.info("%s %s online.", PREFIX, name)
    try:
        passenger: AutoPilotTask = await queue.get()
        await update_passenger(passenger, {'status': AutoPilotTask.RUNNING})

        while passenger.status == AutoPilotTask.RUNNING:
            etrade: AsyncEtrade = await get_provider(passenger)
            override_signal = await refresh_passenger_signal(passenger)
            has_green_light = await green_light(name, passenger, etrade)

            if not has_green_light:
                continue

            if override_signal == AutoPilotTask.BUY or passenger.state == AutoPilotTask.BUYING:
                await buy_position(name, passenger)
            elif override_signal == AutoPilotTask.SELL or passenger.state == AutoPilotTask.SELLING:
                await sell_position(name, passenger)
            else:
                await track_position(name, passenger)

            # get quote
            # get position
            # determine if needs to sell
            # if sell, go into selling mode

            # for _ in range(3):
            #     print(f'{pilot.symbol + ":":<6} getting quote...')
            #     start = time.perf_counter()
            #     quote = await etrade.get_quote(pilot.symbol)
            #     elapsed = time.perf_counter() - start
            #     last_price = Decimal(str(quote.get("All").get("lastTrade")))
            #     print(f'{pilot.symbol + ":":<6} {last_price} {"":>20} {elapsed:0.2f} sec')
            #     print(f'{pilot.symbol + ":":<6} sleeping 1 sec')
            #     await asyncio.sleep(1)
        await delete_passenger(passenger)
    except asyncio.CancelledError:
        logger.info("%s %s stopping...", PREFIX, name)

    except Exception as exception:  # pylint: disable=broad-except
        logger.error("%s %s %s: %s", PREFIX, name,
                     type(exception).__name__,
                     str(exception), exc_info=1)
    finally:
        logger.info("%s %s done.", PREFIX, name)
        queue.task_done()


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
            # logger.debug("%s no passengers. sleeping for 1 sec.", PREFIX)
            await asyncio.sleep(1)
            continue

        logger.debug("%s %s passengers in line.", PREFIX, len(passengers))
        for passngr in passengers:
            driver_name = f'driver-{passngr.user_id}-{passngr.symbol}'
            logger.debug("%s creating %s...", PREFIX, driver_name)
            await queue.put(passngr)
            await update_passenger(passngr, {'status': AutoPilotTask.QUEUED})
            asyncio.create_task(
                driver(driver_name, queue))
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
