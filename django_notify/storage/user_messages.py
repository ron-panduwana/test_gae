"""
Storages used to assist in the deprecation of contrib.auth User messages.

"""
from django_notify.storage.base import BaseStorage, Notification
from django.contrib.auth.models import User
from django_notify.storage.fallback import FallbackStorage


class UserMessagesStorage(BaseStorage):
    """
    Read-only temporary notification storage which retrieves messages from
    the User.
    
    """
    session_key = '_notifications'

    def _get_messages_queryset(self):
        """
        Return the QuerySet containing all user messages (or ``None`` if
        request.user is not a contrib.auth User).
        
        """
        user = getattr(self.request, 'user', None)
        if isinstance(user, User):
            return user.message_set.all()

    def add(self, *args, **kwargs):
        raise NotImplementedError('This message storage is read-only.')

    def _get(self, *args, **kwargs):
        """
        Retrieve a list of messages assigned to the User.
        
        """
        queryset = self._get_messages_queryset()
        if queryset is None:
            # This is a read-only and optional storage, so to ensure other
            # storages will also be read if used with FallbackStorage an empty
            # list is returned rather than None.
            return []
        messages = []
        for user_message in queryset:
            messages.append(Notification(user_message.message))
        return messages

    def _store(self, messages, *args, **kwargs):
        """
        Remove any messages assigned to the User and returns the list of
        messages (since no messages are stored in this read-only storage).
        
        """
        queryset = self._get_messages_queryset()
        if queryset is not None:
            queryset.delete()
        return messages


class LegacyFallbackStorage(FallbackStorage):
    """
    A storage backend which works like ``FallbackStorage`` but also handles
    retrieving (and clearing) contrib.auth User messages.
    
    """
    storage_classes = (UserMessagesStorage,) + FallbackStorage.storage_classes
