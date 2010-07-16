import datetime
import hashlib
import logging
from google.appengine.ext import db
from crlib.models import GDataIndex


_MODELS_DICT = {}

def register(cls):
    _MODELS_DICT[cls.__name__] = cls


class CacheUpdater(object):
    def __init__(self, items_dict, cache_model, model_class):
        self.items_dict = items_dict
        self.cache_model = cache_model
        self.model_class = model_class

    def _item_kwargs(self, item):
        kw = self.model_class._atom_to_kwargs(item._atom)
        to_set = {}

        keys = self.cache_model._properties.keys()
        if 'updated_on' in keys:
            keys.remove('updated_on')

        for key in keys:
            if key in kw:
                to_set[key] = kw[key]
        return to_set

    def add(self, hashes):
        created = []
        for hsh in hashes:
            created.append(self.create(hsh))
        db.put(created)

    def create(self, hsh):
        kw = self._item_kwargs(self.items_dict[hsh])
        return self.cache_model(
            key_name=hsh,
            **kw
        )

    def get(self, hashes):
        return self.cache_model.get_by_key_name(hashes)

    def delete(self, hashes):
        to_delete = [x for x in self.cache_model.get_by_key_name(hashes) if x]
        db.delete(to_delete)


def update_cache(post_data):
    key_name = post_data.get('key_name', 'red.lab.cloudreach.co.uk:GANickname')
    page = post_data.get('page', 0)

    if page:
        key_name += ':%s' % page

    cursor = post_data.get('cursor')
    prev_hashes = post_data.get('hashes', [])

    index = GDataIndex.get_or_insert(
        key_name=key_name,
    )

    domain, model = key_name.split(':')
    model_class = _MODELS_DICT[model]
    items, feed, cursor = model_class.all().retrieve_page(cursor)

    new_page_hash = hashlib.sha1(str(feed)).hexdigest()

    leftover = []

    if new_page_hash != index.page_hash:
        index.page_hash = new_page_hash
        old_hashes = prev_hashes + index.hashes
        index.keys, index.hashes = [], []
        cache_model = model_class._meta.cache_model

        items_dict = {}
        new_hashes = []
        for item in items:
            hsh = hashlib.sha1(str(item._atom)).hexdigest()
            new_hashes.append(hsh)
            items_dict[hsh] = item

        updater = CacheUpdater(items_dict, cache_model, model_class)

        old_s, new_s = set(old_hashes), set(new_hashes)
        common = old_s.intersection(new_s)

        leftover = []

        if cursor and common:
            leftover = _update_middle_page(
                common, old_hashes, new_hashes, updater)
        elif not cursor:
            _update_last_page(
                new_s - old_s, old_s - new_s, key_name, page, updater)
        else:
            leftover = _update_whole_page(old_hashes, new_hashes, updater)

    if not page:
        index.last_updated = datetime.datetime.now()

    index.put()

    if cursor:
        taskqueue.add(url=reverse('new_cache_domain'), params={
            'key_name': request.POST.get('key_name'),
            'page': page + 1,
            'cursor': cursor,
            'hashes': leftover,
        })


def _update_middle_page(common, old_hashes, new_hashes, updater):
    for item in reversed(new_hashes):
        if item in common:
            last_common = item
            break
    old_index = old_hashes.index(last_common)
    new_index = new_hashes.index(last_common)

    old_s = set(old_hashes[:old_index])
    new_s = set(new_hashes[:new_index])

    updater.add(old_s - new_s)
    updater.delete(new_s - old_s)

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


def _update_last_page(added, deleted, key_name, page, updater):
    logging.warning('added: %s' % str(added))
    logging.warning('deleted: %s' % str(deleted))
    updater.add(added)
    updater.delete(deleted)

    keys = [key_name.replace(str(page), str(x)) for x in (page + 1, page + 2)]
    indexes = GDataIndex.get_by_key_name(keys)
    if any(indexes):
        db.delete(indexes)


def _update_whole_page(old_hashes, new_hashes, updater):
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


