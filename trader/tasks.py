import logging

from celery import task

logger = logging.getLogger("trader.tasks")


@task
def test(param1, param2):
    logger.info("executing task: test(param1=%s, param2=%s)",
                param1, param2)
