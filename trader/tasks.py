import logging

from celery import task

# pylint: disable=invalid-name
logger = logging.getLogger("trader.tasks")


@task
def watch_until_executed(order_id):
    logger.info("executing task: watch_until_executed(order_id=%s)",
                order_id)
