import asyncio
import logging
import signal
import time
from datetime import datetime, timedelta
from decimal import Decimal

import httpx
import pytz
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.crypto import get_random_string

from trader.aio.db import database_sync_to_async
from trader.aio.providers import AsyncEtrade
from trader.enums import MarketSession, OrderAction, OrderStatus, PriceType
from trader.models import AutoPilotTask, ProviderSession, ServiceProvider
from trader.providers import ServiceError
from trader.utils import (clean_quote, get_ask, get_bid, get_last,
                          get_limit_price, time_till_market_open)

# pylint: disable=invalid-name
logger = logging.getLogger("trader.autopilot")
PREFIX = "[autopilot]"


@database_sync_to_async
def get_passengers():
    return list(
        AutoPilotTask.objects.all()
        .select_related('provider', 'provider__broker', 'strategy', 'account', 'user')
        .filter(status=AutoPilotTask.READY)
    )


@database_sync_to_async
def recall_stranded_passengers():
    passengers = AutoPilotTask.objects.all() \
        .filter(status=AutoPilotTask.RUNNING)
    passengers.update(status=AutoPilotTask.READY)


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


async def post_webhook(webhook: str, msg: str):
    async with httpx.AsyncClient() as client:
        response = await client.request('POST', webhook, data={'content': msg})
    return response


async def get_provider(pilot: AutoPilotTask):
    stored_session = await get_stored_session(pilot.provider)
    return AsyncEtrade(pilot.provider, stored_session)


async def place_sell_order(passenger: AutoPilotTask, sell_price: Decimal,
                           etrade: AsyncEtrade):
    try:
        limit_price = get_limit_price(
            OrderAction.SELL, sell_price, margin=passenger.strategy.price_margin)
        order_params = {
            'account_key': passenger.account.account_key,
            'market_session': MarketSession.current().value,
            'action': OrderAction.SELL.value,
            'symbol': passenger.symbol,
            'price_type': PriceType.LIMIT.value,
            'quantity': passenger.quantity,
            'limit_price': limit_price
        }

        preview_ids = await etrade.preview_order(
            order_client_id=get_random_string(length=20), **order_params)
        order_id = await etrade.place_order(order_client_id=get_random_string(
            length=20), preview_ids=preview_ids, **order_params)
    except ServiceError:
        logger.error("place_sell_order: params %s", order_params)
        raise

    return order_id


async def buy_position(pilot_name: str, passenger: AutoPilotTask, etrade: AsyncEtrade):
    # get position
    # get quote
    # place order
    # watch order until executed or 5sec
    # cancel order if 5sec passed and no fill or partial
    # repeat untill out of position
    await asyncio.sleep(3)


async def commit_sell(passenger: AutoPilotTask, sell_price: Decimal,
                      etrade: AsyncEtrade):
    order_id = await place_sell_order(passenger, sell_price, etrade)

    update_fields = {'state': AutoPilotTask.SELLING,
                     'tracking_order_id': order_id}
    await update_passenger(passenger, update_fields)


async def sell_position(pilot_name: str, passenger: AutoPilotTask, etrade: AsyncEtrade):
    if not passenger.tracking_order_id:
        quote = await etrade.get_quote(passenger.symbol)
        ask = get_ask(quote)
        await commit_sell(passenger, ask, etrade)
        return

    order = await etrade.get_order_details(passenger.account.account_key,
                                           passenger.tracking_order_id,
                                           passenger.symbol)
    if not order:
        logger.info("%s %s unable to track sell order %s. NOT FOUND.",
                    PREFIX, pilot_name, passenger.tracking_order_id)

        update_fields = {
            'status': AutoPilotTask.PAUSED,
            'state': AutoPilotTask.ERROR,
            'error_message': f'unable to track selling order {passenger.tracking_order_id}. NOT FOUND'}
        await update_passenger(passenger, update_fields)
        return

    details = order.get("OrderDetail")[0]
    status = OrderStatus(details.get("status"))
    limit_price = details.get("limitPrice")

    if status in (OrderStatus.OPEN, OrderStatus.PARTIAL):
        quote = await etrade.get_quote(passenger.symbol)
        bid = get_bid(quote)
        ask = get_ask(quote)
        placed_at = datetime.utcfromtimestamp(
            details.get("placedTime")/1000).replace(tzinfo=pytz.utc)
        elapsed_time = timezone.now() - placed_at
        if elapsed_time >= timedelta(seconds=5) and (limit_price < bid or limit_price > ask):
            try:
                await etrade.cancel_order(passenger.account.account_key,
                                          passenger.tracking_order_id)
            except ServiceError as e:
                if e.error_code == 5001:
                    # This order is currently being executed
                    # or rejected. It cannot be cancelled.
                    return

    elif status == OrderStatus.CANCEL_REQUESTED:
        logger.debug("%s %s cancel for order %s has been requested. waiting...",
                     PREFIX, pilot_name, passenger.tracking_order_id)

    elif status == OrderStatus.CANCELLED:
        logger.debug("%s %s order %s cancelled. placing new sell order...",
                     PREFIX, pilot_name, passenger.tracking_order_id)
        instrument = details.get("Instrument")[0]
        ordered_quantity = instrument.get("orderedQuantity")
        filled_quantity = instrument.get("filledQuantity") or 0
        pending_quantity = int(ordered_quantity) - int(filled_quantity)
        update_fields = {'quantity': pending_quantity}
        await update_passenger(passenger, update_fields)

        quote = await etrade.get_quote(passenger.symbol)
        ask = get_ask(quote)
        await commit_sell(passenger, ask, etrade)

    elif status == OrderStatus.REJECTED:
        logger.warning("%s %s order %s rejected. this case is not being handled.",
                       PREFIX, pilot_name, passenger.tracking_order_id)

    elif status == OrderStatus.EXPIRED:
        logger.warning("%s %s order %s expired. this case is not being handled.",
                       PREFIX, pilot_name, passenger.tracking_order_id)

    elif status == OrderStatus.EXECUTED:
        # get possition
        quantity = await etrade.get_position_quantity(passenger.account.account_key,
                                                      passenger.symbol)
        if quantity in (None, 0):
            update_fields = {'status': AutoPilotTask.DONE}
            await update_passenger(passenger, update_fields)
            instrument = details.get("Instrument")[0]
            avg_execution_price = Decimal(
                instrument.get("averageExecutionPrice"))
            percent = (avg_execution_price -
                       passenger.entry_price) / passenger.entry_price * Decimal(100)
            percent = percent.quantize(Decimal('1'))
            percent_label = "profit" if percent > Decimal(0) else "loss"
            logger.info("%s %s position sold for a %s%% %s",
                        PREFIX, pilot_name, percent, percent_label)
            if passenger.discord_webhook:
                await post_webhook(passenger.discord_webhook,
                                   f"{passenger.symbol} position sold for a {percent}% {percent_label}")
        else:
            # TODO: place sell order for scale out quantity
            update_fields = {'quantity': quantity}
            await update_passenger(passenger, update_fields)
            await commit_sell(passenger, ask, etrade)
    else:
        logger.error("%s %s unhandled status %s for order %s",
                     PREFIX, pilot_name, status, passenger.tracking_order_id)
        update_fields = {
            'status': AutoPilotTask.PAUSED,
            'state': AutoPilotTask.ERROR,
            'error_message': f'unhandled status {status} for order {passenger.tracking_order_id}'}
        await update_passenger(passenger, update_fields)


async def follow_strategy(pilot_name: str, passenger: AutoPilotTask,
                          etrade: AsyncEtrade, quote: dict):
    last = get_last(quote)
    bid = get_bid(quote)
    ask = get_ask(quote)

    if bid < passenger.loss_price or ask > passenger.profit_price or last < passenger.pullback_price:
        if bid < passenger.loss_price:
            logger.debug("%s %s bid reached the loss price, placing sell order at %s",
                         PREFIX, pilot_name, ask)
        elif ask > passenger.profit_price:
            logger.debug("%s %s ask reached the profit price, placing sell order at %s",
                         PREFIX, pilot_name, ask)
        else:
            logger.debug("%s %s last price reached the pullback price, placing sell order at %s",
                         PREFIX, pilot_name, ask)

        order_id = await place_sell_order(passenger, ask, etrade)

        update_fields = {'state': AutoPilotTask.SELLING,
                         'tracking_order_id': order_id}
        await update_passenger(passenger, update_fields)


async def minimize_loss(pilot_name: str, passenger: AutoPilotTask,
                        etrade: AsyncEtrade, quote: dict):
    await follow_strategy(pilot_name, passenger, etrade, quote)

    if passenger.state == AutoPilotTask.SELLING:
        return

    bid = get_bid(quote)
    ref_price_thresdhold = passenger.loss_ref_price + passenger.loss_amount * 2
    if bid > ref_price_thresdhold:
        update_fields = {
            'loss_ref_price': passenger.loss_ref_price + passenger.loss_amount}
        await update_passenger(passenger, update_fields)


async def track_position(pilot_name: str, passenger: AutoPilotTask, etrade: AsyncEtrade):
    logger.debug("%s %s tracking.",
                 PREFIX, pilot_name)

    quote = await etrade.get_quote(passenger.symbol)
    quote = clean_quote(quote)
    last = get_last(quote)
    # passenger.tracking_data['quotes'].append(quote.get('All'))
    if passenger.top_price < last:
        passenger.tracking_data['top'] = str(last)

    if passenger.modifier == AutoPilotTask.FOLLOW_STRATEGY:
        await follow_strategy(pilot_name, passenger, etrade, quote)
    elif passenger.modifier == AutoPilotTask.MINIMIZE_LOSS:
        await minimize_loss(pilot_name, passenger, etrade, quote)
    elif passenger.modifier == AutoPilotTask.MAXIMIZE_PROFIT:
        await follow_strategy(pilot_name, passenger, etrade, quote)
    elif passenger.modifier == AutoPilotTask.MIN_LOSS_MAX_PROFIT:
        await follow_strategy(pilot_name, passenger, etrade, quote)
    else:
        await follow_strategy(pilot_name, passenger, etrade, quote)


async def green_light(pilot_name: str, passenger: AutoPilotTask,
                      etrade: AsyncEtrade) -> bool:
    # handle override signal
    if passenger.signal == AutoPilotTask.MANUAL_OVERRIDE:
        logger.info("%s %s received signal MANUAL_OVERRIDE.",
                    PREFIX, pilot_name)
        logger.info("%s %s releasing control...", PREFIX, pilot_name)
        await update_passenger(passenger, {'status': AutoPilotTask.DONE})
        return False

    # if no market session, sleep until market opens
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

        if passenger.discord_webhook:
            await post_webhook(passenger.discord_webhook,
                               f"{passenger.symbol} tracking...")

        while passenger.status == AutoPilotTask.RUNNING:
            etrade: AsyncEtrade = await get_provider(passenger)
            override_signal = await refresh_passenger_signal(passenger)
            has_green_light = await green_light(name, passenger, etrade)

            if not has_green_light:
                continue

            if override_signal == AutoPilotTask.BUY or passenger.state == AutoPilotTask.BUYING:
                await buy_position(name, passenger, etrade)
            elif override_signal == AutoPilotTask.SELL or passenger.state == AutoPilotTask.SELLING:
                await sell_position(name, passenger, etrade)
            else:
                await track_position(name, passenger, etrade)

        # do not delete, keeping history is better
        # if passenger.status == AutoPilotTask.DONE:
        #     await delete_passenger(passenger)
    except asyncio.CancelledError as e:
        logger.info("%s %s stopping...", PREFIX, name)
        update_fields = {'status': AutoPilotTask.PAUSED,
                         'state': AutoPilotTask.ERROR,
                         'error_message': str(e),
                         'tracking_data': passenger.tracking_data}
        await update_passenger(passenger, update_fields)
        if passenger and passenger.discord_webhook:
            await post_webhook(
                passenger.discord_webhook,
                f"{passenger.symbol} autopilot {AutoPilotTask.TASK_STATUS[passenger.status][1]}. {str(e)}"
            )

    except Exception as exception:  # pylint: disable=broad-except
        logger.error("%s %s %s: %s", PREFIX, name,
                     type(exception).__name__,
                     str(exception), exc_info=1)
        update_fields = {'status': AutoPilotTask.PAUSED,
                         'state': AutoPilotTask.ERROR,
                         'error_message': str(exception),
                         'tracking_data': passenger.tracking_data}
        await update_passenger(passenger, update_fields)
        if passenger and passenger.discord_webhook:
            await post_webhook(
                passenger.discord_webhook,
                f"{passenger.symbol} autopilot {AutoPilotTask.TASK_STATUS[passenger.status][1]}. {str(exception)}"
            )
    finally:
        logger.info("%s %s %s.", PREFIX, name,
                    AutoPilotTask.TASK_STATUS[passenger.status][1])
        update_fields = {'tracking_data': passenger.tracking_data}
        await update_passenger(passenger, update_fields)
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

    # reset any tasks left hanging (e.g: by a system restart)
    logger.debug("%s recovering hanging tasks...", PREFIX)
    await recall_stranded_passengers()

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
            driver_name = f'driver.{passngr.id}/{passngr.symbol}'
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
