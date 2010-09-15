from django_notify import constants
import unittest
from django import http
from django.conf import settings
from django.utils.translation import ugettext_lazy
from django_notify import utils
from django_notify.storage import Storage, base
from django_notify.storage.base import Notification


def add_level_messages(storage):
    """
    Add 6 messages from different levels (including a custom one) to a storage
    instance.
    
    """
    storage.add('A generic message')
    storage.add('Some custom level', level=29)
    storage.debug('A debugging message', extra_tags='extra-tag')
    storage.warning('A warning')
    storage.error('An error')
    storage.success('This was a triumph.')


class BaseTest(unittest.TestCase):
    storage_class = Storage
    restore_settings = ['NOTIFICATIONS_LEVEL', 'NOTIFICATIONS_TAGS']

    def setUp(self):
        self._remembered_settings = {}
        for setting in self.restore_settings:
            if hasattr(settings, setting):
                self._remembered_settings[setting] = getattr(settings, setting)
                delattr(settings._wrapped, setting)

    def tearDown(self):
        for setting in self.restore_settings:
            self.restore_setting(setting)

    def restore_setting(self, setting):
        if setting in self._remembered_settings:
            value = self._remembered_settings.pop(setting)
            setattr(settings, setting, value)
        elif hasattr(settings, setting):
            delattr(settings._wrapped, setting)

    def get_request(self):
        return http.HttpRequest()

    def get_response(self):
        return http.HttpResponse()

    def get_storage(self, data=None):
        """
        Return the storage backend, setting it's loaded data to the ``data``
        argument.
        
        This method avoids the storage ``_get`` method from getting called so
        that other parts of the storage backend can be tested independent of
        the message retrieval logic.
        
        """
        storage = self.storage_class(self.get_request())
        storage._loaded_data = data or []
        return storage

    def test_add(self):
        storage = self.get_storage()
        self.assertFalse(storage.added_new)
        storage.add('Test message 1')
        self.assert_(storage.added_new)
        storage.add('Test message 2', extra_tags='tag')
        self.assertEqual(len(storage), 2)

    def test_add_lazy_translation(self):
        storage = self.get_storage()
        response = self.get_response()

        storage.add(ugettext_lazy('lazy message'))
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 1)

    def test_no_update(self):
        storage = self.get_storage()
        response = self.get_response()
        storage.update(response)
        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 0)

    def test_add_update(self):
        storage = self.get_storage()
        response = self.get_response()

        storage.add('Test message 1')
        storage.add('Test message 1', extra_tags='tag')
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 2)

    def test_existing_add_read_update(self):
        storage = self.get_existing_storage()
        response = self.get_response()

        storage.add('Test message 3')
        list(storage)   # Simulates a read
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 0)

    def test_existing_read_add_update(self):
        storage = self.get_existing_storage()
        response = self.get_response()

        list(storage)   # Simulates a read
        storage.add('Test message 3')
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 1)

    def stored_messages_count(self, storage, response):
        """
        Returns the number of messages being stored after a
        ``storage.update()`` call.
        
        """
        raise NotImplementedError('This method must be set by a subclass.')

    def test_get(self):
        raise NotImplementedError('This method must be set by a subclass.')

    def get_existing_storage(self):
        return self.get_storage([Notification('Test message 1'),
                                 Notification('Test message 2',
                                              extra_tags='tag')])

    def test_existing_read(self):
        """
        Reading the existing storage doesn't cause the data to be lost.
        
        """
        storage = self.get_existing_storage()
        self.assertFalse(storage.used)
        # After iterating the storage engine directly, the used flag is set.
        data = list(storage)
        self.assert_(storage.used)
        # The data does not disappear because it has been iterated.
        self.assertEqual(data, list(storage))

    def test_existing_add(self):
        storage = self.get_existing_storage()
        self.assertFalse(storage.added_new)
        storage.add('Test message 3')
        self.assert_(storage.added_new)

    def test_default_level(self):
        storage = self.get_storage()
        add_level_messages(storage)
        self.assertEqual(len(storage), 5)

    def test_low_level(self):
        storage = self.get_storage()
        storage.level = 5
        add_level_messages(storage)
        self.assertEqual(len(storage), 6)

    def test_high_level(self):
        storage = self.get_storage()
        storage.level = 30
        add_level_messages(storage)
        self.assertEqual(len(storage), 2)

    def test_settings_level(self):
        settings.NOTIFICATIONS_LEVEL = 29
        storage = self.get_storage()
        add_level_messages(storage)
        self.assertEqual(len(storage), 3)

    def test_tags(self):
        storage = self.get_storage()
        storage.level = 0
        add_level_messages(storage)
        tags = [msg.tags for msg in storage]
        self.assertEqual(tags,
                         ['', '', 'extra-tag debug', 'warning', 'error',
                          'success'])

    def test_custom_tags(self):
        settings.NOTIFICATIONS_TAGS = {
            constants.INFO: 'info',
            constants.DEBUG: '',
            constants.WARNING: '',
            constants.ERROR: 'bad',
            29: 'magic'
        }
        # LEVEL_TAGS is a constant defined in django_notify.storage.base
        # module, so after changing settings.NOTIFICATIONS_TAGS, we need to
        # update that constant too.
        base.LEVEL_TAGS = utils.get_level_tags()
        try:
            storage = self.get_storage()
            storage.level = 0
            add_level_messages(storage)
            tags = [msg.tags for msg in storage]
            self.assertEqual(tags,
                         ['info', 'magic', 'extra-tag', '', 'bad', 'success'])
        finally:
            # Ensure the level tags constant is put back like we found it.
            self.restore_setting('NOTIFICATIONS_TAGS')
            base.LEVEL_TAGS = utils.get_level_tags()
