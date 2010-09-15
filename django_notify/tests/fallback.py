from django_notify.storage.base import EOFNotification
from django_notify.storage.fallback import FallbackStorage
from django_notify.tests.base import BaseTest
from django_notify.tests.cookie import set_cookie_data, \
    stored_cookie_messages_count
from django_notify.tests.session import set_session_data, \
    stored_session_messages_count


class FallbackTest(BaseTest):
    storage_class = FallbackStorage

    def get_request(self):
        self.session = {}
        request = super(FallbackTest, self).get_request()
        request.session = self.session
        return request

    def get_cookie_storage(self, storage):
        return storage.storages[-2]

    def get_session_storage(self, storage):
        return storage.storages[-1]

    def stored_cookie_messages_count(self, storage, response):
        return stored_cookie_messages_count(self.get_cookie_storage(storage),
                                            response)

    def stored_session_messages_count(self, storage, response):
        return stored_session_messages_count(self.get_session_storage(storage))

    def stored_messages_count(self, storage, response):
        """
        Return the storage totals from both cookie and session backends,
        subtracting 1 for the EOF.
        
        """
        total = (self.stored_cookie_messages_count(storage, response) +
                 self.stored_session_messages_count(storage, response))
        if total:
            total -= 1
        return total

    def test_get(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)

        # Set initial cookie data.
        example_messages = [str(i) for i in range(5)]
        set_cookie_data(cookie_storage, example_messages + [EOFNotification()])

        # Overwrite the _get method of the fallback storage to prove it is not
        # used (it would cause a TypeError: 'NoneType' object is not callable).
        self.get_session_storage(storage)._get = None

        # Test that the message actually contains what we expect.
        self.assertEqual(list(storage), example_messages)

    def test_get_empty(self):
        request = self.get_request()
        storage = self.storage_class(request)

        # Overwrite the _get method of the fallback storage to prove it is not
        # used (it would cause a TypeError: 'NoneType' object is not callable).
        self.get_session_storage(storage)._get = None

        # Test that the message actually contains what we expect.
        self.assertEqual(list(storage), [])

    def test_get_fallback(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)
        session_storage = self.get_session_storage(storage)

        # Set initial cookie and session data.
        example_messages = [str(i) for i in range(5)]
        set_cookie_data(cookie_storage, example_messages[:4])
        set_session_data(session_storage,
                         example_messages[4:] + [EOFNotification()])

        # Test that the message actually contains what we expect.
        self.assertEqual(list(storage), example_messages)


    def test_get_fallback_only(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)
        session_storage = self.get_session_storage(storage)

        # Set initial cookie and session data.
        example_messages = [str(i) for i in range(5)]
        set_cookie_data(cookie_storage, [], encode_empty=True)
        set_session_data(session_storage,
                         example_messages + [EOFNotification()])

        # Test that the message actually contains what we expect.
        self.assertEqual(list(storage), example_messages)

    def test_flush_used_backends(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)
        session_storage = self.get_session_storage(storage)

        # Set initial cookie and session data.
        set_cookie_data(cookie_storage, ['cookie'])
        set_session_data(session_storage, ['session'])

        # When updating, previously used but no longer needed backends are
        # flushed.
        response = self.get_response()
        list(storage)
        storage.update(response)
        session_storing = self.stored_session_messages_count(storage, response)
        self.assertEqual(session_storing, 0)

    def test_no_fallback(self):
        """
        A short number of messages which data size doesn't exceed what is
        allowed in a cookie will all be stored in the CookieBackend.
        
        If the CookieBackend can store all messages, the SessionBackend will be
        written to at all.
        
        """
        storage = self.get_storage()
        response = self.get_response()

        # Overwrite the _store method of the fallback storage to prove it is not
        # used (it would cause a TypeError: 'NoneType' object is not callable).
        self.get_session_storage(storage)._store = None

        for i in range(5):
            storage.add(str(i) * 100)
        storage.update(response)

        cookie_storing = self.stored_cookie_messages_count(storage, response)
        self.assertEqual(cookie_storing, 6)   # 5 + EOF
        session_storing = self.stored_session_messages_count(storage, response)
        self.assertEqual(session_storing, 0)

    def test_session_fallback(self):
        """
        If the data exceeds what is allowed in a cookie, older messages which
        did not "fit" are stored in the SessionBackend.
        
        """
        storage = self.get_storage()
        response = self.get_response()

        for i in range(5):
            storage.add(str(i) * 900)
        storage.update(response)

        cookie_storing = self.stored_cookie_messages_count(storage, response)
        self.assertEqual(cookie_storing, 4)
        session_storing = self.stored_session_messages_count(storage, response)
        self.assertEqual(session_storing, 2)   # 1 remaining + EOF

        session_messages = list(self.get_session_storage(storage))
        self.assert_(isinstance(session_messages[-1], EOFNotification))

    def test_session_fallback_only(self):
        """
        If the data exceeds what is allowed in a cookie, older messages which
        did not "fit" are stored in the SessionBackend.
        
        """
        storage = self.get_storage()
        response = self.get_response()

        storage.add('x' * 5000)
        storage.update(response)

        cookie_storing = self.stored_cookie_messages_count(storage, response)
        self.assertEqual(cookie_storing, 0)
        session_storing = self.stored_session_messages_count(storage, response)
        self.assertEqual(session_storing, 2)   # 1 message + EOF

        session_messages = list(self.get_session_storage(storage))
        self.assert_(isinstance(session_messages[-1], EOFNotification))
