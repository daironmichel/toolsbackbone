import logging

from celery import task

# pylint: disable=invalid-name
logger = logging.getLogger("trader.tasks")


@task
def watch_until_executed(order_id):
    logger.info("executing task: test(param1=%s, param2=%s)",
                param1, param2)
