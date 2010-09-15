from hashlib import sha1
from django.conf import settings
from django_notify import constants
from django_notify.storage.base import BaseStorage, Notification, \
                                       EOFNotification
try:
    import json   # Available in Python 2.6.
except ImportError:
    # Otherwise fall back to simplejson bundled with Django.
    from django.utils import simplejson as json


class NotificationEncoder(json.JSONEncoder):
    """
    A JSON encoder which also compactly serializes ``Notification`` and
    ``EOFNotification`` classes.
    
    """
    notification_key = '__json_notification'
    notification_eof_key = '__json_notification_eof'

    def default(self, obj):
        if isinstance(obj, Notification):
            notification = [self.notification_key, obj.message]
            default_level = obj.level == constants.INFO
            if not default_level or obj.extra_tags:
                notification.append(obj.level)
                if obj.extra_tags:
                    notification.append(obj.extra_tags)
            return notification
        if isinstance(obj, EOFNotification):
            return [self.notification_eof_key]
        return super(NotificationEncoder, self).default(obj)


class NotificationDecoder(json.JSONDecoder):
    """
    A JSON decoder which additionally supports serialized ``Notification`` and
    ``EOFNotification`` classes.
    
    """
    def process_notifications(self, obj):
        if isinstance(obj, list) and obj:
            if obj[0] == NotificationEncoder.notification_key: 
                return Notification(*obj[1:])
            if NotificationEncoder.notification_eof_key in obj:
                return EOFNotification()
            return [self.process_notifications(item) for item in obj]
        if isinstance(obj, dict):
            return dict([(key, self.process_notifications(value))
                         for key, value in obj.iteritems()])
        return obj

    def decode(self, s, **kwargs):
        decoded = super(NotificationDecoder, self).decode(s, **kwargs)
        return self.process_notifications(decoded)


class CookieStorage(BaseStorage):
    """
    Cookie based temporary notification storage backend.
    
    """
    cookie_name = 'notifications'
    max_cookie_size = 4096

    def _get(self, *args, **kwargs):
        """
        Retrieve a list of messages from the notifications cookie.
        
        """
        data = self.request.COOKIES.get(self.cookie_name)
        return self._decode(data)

    def _update_cookie(self, encoded_data, response):
        """
        Either set the cookie with the encoded data if there is any data to
        store, otherwise delete the cookie.
        
        """
        if encoded_data:
            response.set_cookie(self.cookie_name, encoded_data)
        else:
            response.delete_cookie(self.cookie_name)

    def _store(self, messages, response, remove_oldest=True, *args, **kwargs):
        """
        Store the messages to a cookie, returning a list of any messages which
        could not be stored.
        
        If the encoded data is larger than ``max_cookie_size``, remove messages
        until the data fits (these are the messages which are returned).
        
        """
        unstored_messages = []
        encoded_data = self._encode(messages)
        if self.max_cookie_size:
            while encoded_data and len(encoded_data) > self.max_cookie_size:
                if remove_oldest:
                    unstored_messages.append(messages.pop(0))
                else:
                    unstored_messages.insert(0, messages.pop())
                encoded_data = self._encode(messages,
                                            encode_empty=unstored_messages)
        self._update_cookie(encoded_data, response)
        return unstored_messages

    def _hash(self, value):
        """
        Create a SHA1 hash based on the value combined with the project
        setting's SECRET_KEY.
        
        """
        return sha1(value + settings.SECRET_KEY).hexdigest()

    def _encode(self, messages, encode_empty=False):
        """
        Return an encoded version of the messages list which can be stored as
        plain text.
        
        Since the data will be retrieved from the client-side, the encoded data
        also contains a hash to ensure that the data was not tampered with.
        
        """
        if messages or encode_empty:
            encoder = NotificationEncoder(separators=(',', ':'))
            value = encoder.encode(messages)
            return '%s$%s' % (self._hash(value), value)

    def _decode(self, data):
        """
        Safely decode a encoded text stream back into a list of messages.
        
        If the encoded text stream contained an invalid hash or was in an
        invalid format, ``None`` is returned.
        
        """
        if not data:
            return None
        bits = data.split('$', 1)
        if len(bits) == 2:
            hash, value = bits
            if hash == self._hash(value):
                try:
                    # If we get here (and the JSON decode works), everything is
                    # good. In any other case, drop back and return None.
                    return json.loads(value, cls=NotificationDecoder)
                except:
                    pass
        # Mark the data as used (so it gets removed) since something was wrong
        # with the data.
        self.used = True
        return None
