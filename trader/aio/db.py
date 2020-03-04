from asgiref.sync import SyncToAsync
from django.db import close_old_connections, connections


class DatabaseSyncToAsync(SyncToAsync):
    """
    SyncToAsync version that cleans up old database connections when it exits.
    """

    def thread_handler(self, loop, *args, **kwargs):
        # close_old_connections()
        connections.close_all()
        try:
            return super().thread_handler(loop, *args, **kwargs)
        finally:
            connections.close_all()
            # close_old_connections()


# The class is TitleCased, but we want to encourage use as a callable/decorator
database_sync_to_async = DatabaseSyncToAsync
