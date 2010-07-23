import datetime
import hashlib
import logging
import pickle
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from django.core.urlresolvers import reverse
from crlib.models import GDataIndex
from crauth.models import AppsDomain
from crauth import users


MIN_DATETIME = datetime.datetime(1970, 1, 1)

_MODELS_DICT = {}

def register(cls):
    _MODELS_DICT[cls.__name__] = cls


def ensure_has_cache(domain, model_class):
    if model_class in _MODELS_DICT:
        key_name = '%s:%s' % (domain, model_class)
        index = GDataIndex.get_by_key_name(key_name)
        if not index:
            index = GDataIndex(
                key_name=key_name,
                domain=domain,
                model_class=model_class,
                last_updated=MIN_DATETIME,
            )
            index.put()
            taskqueue.add(url=reverse('precache_domain_item'), params={
                'key_name': key_name,
            })


def prepare_indexes(domain):
    for key in _MODELS_DICT.iterkeys():
        key_name = '%s:%s' % (domain, key)
        GDataIndex.get_or_insert(
            key_name=key_name,
            domain=domain,
            model_class=key,
            last_updated=MIN_DATETIME,
        )


class _CacheUpdater(object):
    def __init__(self, items_dict, cache_model, model_class, domain, index):
        self.items_dict = items_dict
        self.cache_model = cache_model
        self.model_class = model_class
        self.domain = domain
        self.index = index

    def add(self, hashes):
        created = []
        for hsh in hashes:
            created.append(self.create(hsh))
        db.put(created)

    def create(self, hsh):
        item = self.items_dict[hsh]
        return self.cache_model.from_model(
            item,
            key_name=hsh,
            _domain=self.domain,
            _atom=item._atom,
            _index=self.index,
            _gdata_key_name=item.key(),
        )

    def get(self, hashes):
        return self.cache_model.get_by_key_name(hashes)

    def delete(self, hashes):
        to_delete = [x for x in self.cache_model.get_by_key_name(hashes) if x]
        db.delete(to_delete)


DEFAULT_KEY_NAME = 'red.lab.cloudreach.co.uk:SharedContact'

def update_cache(post_data):
    key_name = post_data.get('key_name', DEFAULT_KEY_NAME)
    page = int(post_data.get('page', 0))

    if page:
        key_name += ':%s' % page

    if memcache.incr('lock:' + key_name, initial_value=0) > 1:
        return

    cursor = post_data.get('cursor')
    prev_hashes = post_data.get('hashes', []) or []
    if prev_hashes:
        prev_hashes = prev_hashes.split(':')

    domain, model = post_data.get(
        'key_name', DEFAULT_KEY_NAME).split(':')

    index = GDataIndex.get_or_insert(
        key_name=key_name,
        domain=domain,
        model_class=model,
    )

    apps_domain = AppsDomain.get_by_key_name(domain)
    users._set_current_user(apps_domain.admin_email, domain)

    model_class = _MODELS_DICT.get(model)
    if not model_class or (hasattr(model_class._meta, 'no_auto_cache') and
                           model_class._meta.no_auto_cache):
        return

    items, feed, cursor = model_class.all().retrieve_page(cursor)
    items = list(items)

    cache_model = model_class._meta.cache_model
    if hasattr(cache_model, 'additional_cache'):
        cache_model.additional_cache(items, index, domain)

    new_page_hash = hashlib.sha1(str(feed)).hexdigest()

    leftover = []

    if new_page_hash != index.page_hash:
        index.page_hash = new_page_hash
        old_hashes = prev_hashes + index.hashes
        index.keys, index.hashes = [], []

        items_dict = {}
        new_hashes = []
        new_keys = []
        for item in items:
            hsh = hashlib.sha1(str(item._atom)).hexdigest()
            new_hashes.append(hsh)
            items_dict[hsh] = item
            new_keys.append(item.key())

        updater = _CacheUpdater(items_dict, cache_model, model_class, domain,
                                index)

        old_s, new_s = set(old_hashes), set(new_hashes)
        common = old_s.intersection(new_s)

        leftover = []

        if cursor and common:
            leftover = _update_middle_page(
                updater, common, old_hashes, new_hashes)
        elif not cursor:
            _update_last_page(
                updater, new_s - old_s, old_s - new_s, key_name, page)
        else:
            leftover = _update_whole_page(updater, old_hashes, new_hashes)

        index.hashes = new_hashes
        index.keys = new_keys

    if not page:
        index.last_updated = datetime.datetime.now()

    index.put()

    if cursor:
        taskqueue.add(url=reverse('precache_domain_item'), params={
            'key_name': post_data.get('key_name', DEFAULT_KEY_NAME),
            'page': page + 1,
            'cursor': cursor,
            'hashes': ':'.join(leftover),
        })

    memcache.delete('lock:' + key_name)


def _update_middle_page(updater, common, old_hashes, new_hashes):
    for item in reversed(new_hashes):
        if item in common:
            last_common = item
            break
    old_index = old_hashes.index(last_common)
    new_index = new_hashes.index(last_common)

    old_s = set(old_hashes[:old_index])
    new_s = set(new_hashes[:new_index])

    updater.add(new_s - old_s)
    updater.delete(old_s - new_s)

    # Check if any of remaining new hashes is in db
    # If it is - we may remove all of the remaining old hashes
    leftover = []
    new_leftover = new_hashes[new_index:]
    existing = updater.get(new_leftover)
    if any(existing):
        updater.delete(old_hashes[old_index:])
    else:
        leftover = old_hashes[old_index:]

    created = []
    for hsh, obj in zip(new_leftover, existing):
        if not obj:
            created.append(updater.create(hsh))
    db.put(created)

    return leftover


def _update_last_page(updater, added, deleted, key_name, page):
    updater.add(added)
    updater.delete(deleted)

    keys = [key_name.replace(str(page), str(x)) for x in (page + 1, page + 2)]
    indexes = GDataIndex.get_by_key_name(keys)
    if any(indexes):
        db.delete(indexes)


def _update_whole_page(updater, old_hashes, new_hashes):
    # old_hashes and new_hashes don't have any common elements

    existing = updater.get(new_hashes)

    leftover = []
    if any(existing):
        updater.delete(old_hashes)
    else:
        leftover = old_hashes[:]

    created = []
    for hsh, obj in zip(new_hashes, existing):
        if not obj:
            created.append(updater.create(hsh))
    db.put(created)

    return leftover

