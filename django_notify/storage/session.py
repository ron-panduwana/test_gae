from django_notify.storage.base import BaseStorage


class SessionStorage(BaseStorage):
    """
    Session based temporary notification storage.
    
    """
    session_key = '_notifications'

    def __init__(self, request, *args, **kwargs):
        assert hasattr(request, 'session'), "The session-based temporary "\
            "notification storage requires session middleware to be installed."
        super(SessionStorage, self).__init__(request, *args, **kwargs)

    def _get(self, *args, **kwargs):
        """
        Retrieve a list of messages from the request's session.
        
        """
        return self.request.session.get(self.session_key)

    def _store(self, messages, response, *args, **kwargs):
        """
        Store a list of messages to the request's session.
        
        """
        if messages:
            self.request.session[self.session_key] = messages
        else:
            self.request.session.pop(self.session_key, None)
