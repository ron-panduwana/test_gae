from django.conf import settings
from django.utils.encoding import force_unicode, StrAndUnicode
from django_notify import constants, utils


LEVEL_TAGS = utils.get_level_tags()


class Notification(StrAndUnicode):
    """
    A notification message.
    
    """
    def __init__(self, message, level=None, extra_tags=None):
        self.message = message
        self.extra_tags = extra_tags
        if level is None:
            self.level = constants.INFO
        else:
            self.level = int(level)

    def _prepare(self):
        """
        Prepare the notification for serialization by forcing the ``message``
        and ``tags`` to unicode in case they are lazy translations.
        
        Known "safe" types (None, int, etc.) are not converted (see Django's
        ``force_unicode`` implementation for details).
        
        """
        self.message = force_unicode(self.message, strings_only=True)

    def __unicode__(self):
        return force_unicode(self.message)

    def _get_tags(self):
        label_tag = force_unicode(LEVEL_TAGS.get(self.level, ''),
                                  strings_only=True)
        extra_tags = force_unicode(self.extra_tags, strings_only=True)
        if extra_tags:
            if label_tag:
                return u'%s %s' % (extra_tags, label_tag)
            return extra_tags
        return label_tag or ''

    tags = property(_get_tags)


class EOFNotification:
    """
    A notification class which indicates the end of the message stream (i.e. no
    further message retrieval is required).
    
    Not used in all storage classes.
    
    """


class BaseStorage(object):
    """
    Base backend for temporary notification storage.
    
    This is not a complete class, to be a usable storage backend, it must be
    subclassed and the two methods ``_get`` and ``_store`` overridden.
    
    """
    store_serialized = True

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self._queued_messages = []
        self.used = False
        self.added_new = False
        super(BaseStorage, self).__init__(*args, **kwargs)

    def __len__(self):
        return len(self._loaded_messages) + len(self._queued_messages)

    def __iter__(self):
        self.used = True
        if self._queued_messages:
            self._loaded_messages.extend(self._queued_messages)
            self._queued_messages = []
        return iter(self._loaded_messages)

    def __contains__(self, item):
        return item in self._loaded_messages or item in self._queued_messages

    @property
    def _loaded_messages(self):
        """
        Return a list of loaded messages, retrieving them first if they have
        not been loaded yet.
        
        """
        if not hasattr(self, '_loaded_data'):
            self._loaded_data = self._get() or []
        return self._loaded_data

    def _get(self, *args, **kwargs):
        """
        Retrieve a list of stored messages.
        
        **This method must be implemented by a subclass.**
        
        If it is possible to tell if the backend was not used (as opposed to
        just containing no messages) then ``None`` should be returned.
        
        """
        raise NotImplementedError()

    def _store(self, messages, response, *args, **kwargs):
        """
        Store a list of messages, returning a list of any messages which could
        not be stored.
        
        Two types of objects must be able to be stored, ``Notification`` and
        ``EOFNotification``.
        
        **This method must be implemented by a subclass.**
        
        """
        raise NotImplementedError()

    def _prepare_notifications(self, notifications):
        """
        Prepare a list of notifications for storage.
        
        """
        if self.store_serialized:
            for notification in notifications:
                notification._prepare()

    def update(self, response, fail_silently=True):
        """
        Store all unread messages.
        
        If the backend has yet to be iterated, previously stored messages will
        be stored again. Otherwise, only messages added after the last
        iteration will be stored.
        
        """
        if self.used:
            self._prepare_notifications(self._queued_messages)
            return self._store(self._queued_messages, response)
        elif self.added_new:
            notifications = self._loaded_messages + self._queued_messages
            self._prepare_notifications(notifications)
            return self._store(notifications, response)

    def add(self, message, level=None, extra_tags=''):
        """
        Queue a message to be stored.
        
        The message is only queued if it contained something and its level is
        not less than the recording level (``self.level``).
        
        """
        if not message:
            return
        # Check that the message level is not less than the recording level.
        if level is None:
            level = constants.INFO
        else:
            level = int(level)
        if level < self.level:
            return
        # Add the message.
        self.added_new = True
        notification = Notification(message, level=level,
                                    extra_tags=extra_tags)
        self._queued_messages.append(notification)

    def debug(self, message, extra_tags=''):
        """
        Helper method to add a message with the DEBUG level.
        
        """
        self.add(message, level=constants.DEBUG, extra_tags=extra_tags)

    def success(self, message, extra_tags=''):
        """
        Helper method to add a message with the ``SUCCESS`` level.
        
        """
        self.add(message, level=constants.SUCCESS, extra_tags=extra_tags)

    def warning(self, message, extra_tags=''):
        """
        Helper method to add a message with the ``WARNING`` level.
        
        """
        self.add(message, level=constants.WARNING, extra_tags=extra_tags)

    def error(self, message, extra_tags=''):
        """
        Helper method to add a message with the ``ERROR`` level.
        
        """
        self.add(message, level=constants.ERROR, extra_tags=extra_tags)

    def _get_level(self):
        """
        Return the minimum recorded level.
        
        The default level is the ``NOTIFICATIONS_LEVEL`` setting. If this is
        not found, the ``INFO`` level is used.
        
        """
        if not hasattr(self, '_level'):
            self._level = getattr(settings, 'NOTIFICATIONS_LEVEL',
                                  constants.INFO)
        return self._level

    def _set_level(self, value=None):
        """
        Set a custom minimum recorded level.
        
        If set to ``None``, the default level will be used (see the
        ``_get_level`` method).
        
        """
        if value is None:
            if hasattr(self, '_level'):
                del self._level
        else:
            self._level = int(value)

    level = property(_get_level, _set_level, _set_level)
