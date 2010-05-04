import datetime
import logging
import time
from google.appengine.api import memcache
from openid.association import Association as xAssociation
from openid.store import nonce
from openid.store.interface import OpenIDStore
from auth.models import Association


class DatastoreStore(OpenIDStore):
    def storeAssociation(self, server_url, assoc):
        assoc = Association(
            key_name='%s:%s' % (server_url, str(assoc.handle)),
            url=server_url,
            handle=assoc.handle,
            association=assoc.serialize())
        assoc.put()

    def getAssociation(self, server_url, handle=None):
        assoc = Association.get_by_key_name('%s:%s' % (server_url, str(handle)))
        if assoc is None:
            return None
        assoc = xAssociation.deserialize(assoc.association)
        if assoc.getExpiresIn() <= 0:
            assoc.delete()
            return None
        return assoc

    def removeAssociation(self, server_url, handle):
        assoc = Association.get_by_key_name('%s:%s' % (server_url, str(handle)))
        if assoc is not None:
            assoc.delete()

    def useNonce(self, server_url, timestamp, salt):
        if abs(timestamp - time.time()) > nonce.SKEW:
            return False

        anonce = str((str(server_url), int(timestamp), str(salt)))
        result = memcache.get(anonce)
        if result:
            return False

        memcache.set(anonce, True, nonce.SKEW)
        return True

    def cleanupNonces(self):
        return 0


