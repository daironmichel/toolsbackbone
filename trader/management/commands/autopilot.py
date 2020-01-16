import asyncio
import time

import asgiref
import httpx
from django.core.management.base import BaseCommand, CommandError

from trader.aio.db import database_sync_to_async
from trader.models import AutoPilot


@database_sync_to_async
def get_pilots():
    return list(AutoPilot.objects.all())


async def drive(pilot: AutoPilot):
    print(f"watching {pilot.symbol} for 1s")
    await asyncio.sleep(1)
    return pilot.symbol


async def main():
    print("starting...")
    pilots = await get_pilots()
    res = await asyncio.gather(*[drive(p) for p in pilots])
    print(f'res: {res}')


class Command(BaseCommand):
    help = 'Follow positions and determine when to exit'

    def add_arguments(self, parser):
        # parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        asyncio.run(main())
