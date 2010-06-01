import pickle
from google.appengine.api import memcache
#from lib.gdata import urlfetch as gdata_urlfetch
from lib.gdata.alt import appengine


__all__ = ['run_on_appengine', 'delete_url_from_cache']


MEMCACHE_KEY = 'http_response:%s'


def run_on_appengine(gdata_service):
    gdata_service.http_client = _CachedHttpClient()


def delete_url_from_cache(url):
    memcache.delete(MEMCACHE_KEY % url)


def _http_response_from_cache(value):
    return gdata_urlfetch.HttpResponse(
        _UrlfetchResponse(pickle.loads(value)))


def _http_response_to_cache(response):
    to_cache = {
        'content': response.body.read(),
        'headers': response.headers,
        'status_code': response.status,
    }
    return pickle.dumps(to_cache, pickle.HIGHEST_PROTOCOL)


#class _CachedHttpClient(gdata_urlfetch.AppEngineHttpClient):
class _CachedHttpClient(object):
    def __init__(self, headers=None):
        self.debug = False
        self.headers = headers or {}

    def request(self, operation, url, data=None, headers=None):
        # we only cache get requests
        if operation != 'GET':
            delete_url_from_cache(url)
            #super(_CachedHttpClient, self).request(
            #    operation, url, data, headers)
            return self.http_client.request(operation, url, data, headers)

        key = MEMCACHE_KEY % url

        cached = memcache.get(key)
        if cached is not None:
            try:
                return _http_response_from_cache(cached)
            except Exception:
                delete_url_from_cache(url)

        #response = super(_CachedHttpClient, self).request(
        #    operation, url, data, headers)
        response = self.http_client.request(operation, url, data, headers)
        memcache.set(key, _http_response_to_cache(response))
        return response
gdata_urlfetch.run_on_appengine(_CachedHttpClient)


class _UrlfetchResponse(object):
    def __init__(self, d):
        self.content = d['content']
        self.headers = d['headers']
        self.status_code = d['status_code']


