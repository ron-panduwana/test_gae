import hashlib
import logging
import urllib
from google.appengine.api import memcache


HASH_LEN = 12


class Paginator(object):
    def __init__(self, model_class, request, valid_sortby, per_page=50,
                 query=None):
        self.model_class = model_class
        self.path = request.path
        self.params = request.GET
        self.per_page = per_page

        self.sortby = self.order = self.params.get('sortby')
        self.asc = self.params.get('asc', 'true') == 'true'
        if not self.sortby in valid_sortby:
            self.sortby = self.order = valid_sortby[0]
        if not self.asc:
            self.order = '-' + self.order

        def _query_gen():
            if query:
                return query()
            return model_class.all().order(self.order)
        self.query_gen = _query_gen

        self.query = self.query_gen()

        self.start = self.params.get('start')
        if self.start:
            current_cursor = memcache.get('users:' + self.start)
            if current_cursor:
                self.query.with_cursor(current_cursor)
            self.page = int(self.params.get('page', 0))
        else:
            self.page = 0

        self.from_ = self.page * per_page + 1
        self.to = self.from_ - 1

    def _url(self, params):
        return ('%s?%s' % (self.path, urllib.urlencode(params))).rstrip('?')

    @property
    def objects(self):
        for object in self.query.fetch(self.per_page):
            self.to += 1
            yield object

        self.cursor = self.query.cursor()

    def has_more(self):
        return self.query_gen().with_cursor(self.cursor).get() is not None

    @property
    def next_link(self):
        if self.has_more():
            hashed = hashlib.sha1(self.cursor).hexdigest()[:HASH_LEN]
            memcache.set('users:' + hashed, self.cursor)
            if self.start:
                memcache.set('users_prev:' + hashed, self.start)

            params = dict(self.params.iteritems())
            params['start'] = hashed
            params['page'] = self.page + 1
            return self._url(params)

    @property
    def prev_link(self):
        if self.start:
            params = dict(self.params.iteritems())
            params.pop('start', None)

            prev_start = memcache.get('users_prev:' + self.start)
            if prev_start:
                params['start'] = prev_start
            params['page'] = self.page - 1
            return self._url(params)

    @property
    def from_to(self):
        return '%d - %d' % (self.from_, max(1, self.to))

