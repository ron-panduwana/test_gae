from django.conf import settings
from django_notify.storage import Storage


class NotificationsMiddleware(object):
    """
    Middleware which handles temporary notifications.
    
    """
    def process_request(self, request):
        request.notifications = Storage(request)

    def process_response(self, request, response):
        """
        Update the storage backend (i.e. save the messages).
        
        If not all messages could not be stored and ``DEBUG`` is ``True``, a
        ``ValueError`` will be raised.
        
        """
        # A higher middleware layer may return a request which does not contain
        # notifications storage, so make no assumption that it will be there.
        if hasattr(request, 'notifications'):
            unstored_messages = request.notifications.update(response)
            if unstored_messages and settings.DEBUG:
                raise ValueError('Not all temporary notification messages '
                                 'could be stored.')
        return response
