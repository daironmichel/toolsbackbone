import logging

from asgiref.sync import SyncToAsync
from django.db import close_old_connections, connections

logger = logging.getLogger('trader')


class DatabaseSyncToAsync(SyncToAsync):
    """
    SyncToAsync version that cleans up old database connections when it exits.
    """

    def thread_handler(self, loop, *args, **kwargs):
        close_old_connections()
        # connections.close_all()
        try:
            return super().thread_handler(loop, *args, **kwargs)
        finally:
            # connections.close_all()
            close_old_connections()
            if len(connections.all()) > 5:
                logger.info('closing %s open connections',
                            len(connections.all()))
                connections.close_all()


# The class is TitleCased, but we want to encourage use as a callable/decorator
database_sync_to_async = DatabaseSyncToAsync
