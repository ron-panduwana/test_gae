import datetime
import logging
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.conf import settings
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from crauth import users
from crauth.models import AppsDomain
from crgappspanel import models
from crlib.models import LastCacheUpdate
from crlib import mappers, gdata_wrapper


_CACHE_UPDATE_INTERVAL = 5 * 60 # 5 minutes


# These mappers are required to contain retrieve_all() method taking use_cache
# boolean keyword argument.
_MAPPERS_LIST = (
    mappers.UserEntryMapper,
    mappers.GroupEntryMapper,
    mappers.NicknameEntryMapper,
    mappers.SharedContactEntryMapper,
)

_MAPPERS_DICT = {}
for mapper in _MAPPERS_LIST:
    _MAPPERS_DICT[mapper.__name__] = mapper


_MODELS_LIST = (
    models.GAUser,
)

_MODELS_DICT = {}
for model in _MODELS_LIST:
    _MODELS_DICT[model.__name__] = model


def new_cache_all_domains(request):
    from crlib.models import GDataIndex

    treshold = datetime.datetime.now() - datetime.timedelta(
        seconds=_CACHE_UPDATE_INTERVAL)
    to_update = GDataIndex.all().filter(
        'last_updated <', treshold).order('last_updated').fetch(100)
    for item in to_update:
        taskqueue.add(url=reverse('new_cache_domain'), params={
            'key_name': item.key().name(),
        })
    return HttpResponse(str(len(to_update)))


def _item_kwargs(item, model, cache_model):
    keys = cache_model._properties.keys()
    kw = model._atom_to_kwargs(item._atom)
    to_set = {}
    for key in keys:
        if key in kw:
            to_set[key] = kw[key]
    return to_set


def _create_item(hsh, atom, model, cache_model):
    kw = _item_kwargs(atom, model, cache_model)
    return cache_model(
        key_name=hsh,
        **kw
    )


def _add_delete(added, deleted, model, cache_model, items_dict):
    logging.warning('added: %s' % str(added))
    logging.warning('deleted: %s' % str(deleted))

    to_delete = [x for x in cache_model.get_by_key_name(deleted) if x]
    db.delete(to_delete)

    created = []
    for hsh in added:
        created.append(_create_item(hsh, items_dict[hsh], model, cache_model))
    db.put(created)


def new_cache_domain(request):
    import hashlib
    from crgappspanel.models import GAUser
    from crlib.models import GDataIndex, UserCache

    key_name = request.POST.get('key_name', 'red.lab.cloudreach.co.uk:GAUser')
    page = request.POST.get('page', 0)
    if page:
        key_name += ':%s' % page
    cursor = request.POST.get('cursor')
    prev_hashes = request.POST.get('hashes', [])

    index = GDataIndex.get_or_insert(
        key_name=key_name,
    )

    domain, model = key_name.split(':')

    model_class = _MODELS_DICT[model]
    items, feed, cursor = model_class.all().retrieve_page(cursor)

    feed_xml = str(feed)
    hashed = hashlib.sha1(feed_xml).hexdigest()
    if hashed == index.page_hash:
        return HttpResponse('Sie zgadza!')

    index.page_hash = hashed

    if not page:
        index.last_updated = datetime.datetime.now()

    hashes = prev_hashes + index.hashes
    logging.warning('hashes: %s' % str(hashes))

    index.keys, index.hashes = [], []
    cache_model = model_class._meta.cache_model
    keys = cache_model._properties.keys()
    if 'updated_on' in keys:
        keys.remove('updated_on')

    items_dict = {}
    new_hashes = []
    for item in items:
        hsh = hashlib.sha1(str(item._atom)).hexdigest()
        new_hashes.append(hsh)
        items_dict[hsh] = item
    logging.warning('new_hashes: %s' % str(new_hashes))

    old_s, new_s = set(hashes), set(new_hashes)
    common = old_s.intersection(new_s)

    leftover = []
    if cursor and common:
        for item in reversed(new_hashes):
            if item in common:
                last_common = item
                break
        old_index = hashes.index(last_common)
        new_index = new_hashes.index(last_common)

        old_s = set(hashes[:old_index])
        new_s = set(new_hashes[:new_index])

        deleted = old_s - new_s
        added = new_s - old_s

        _add_delete(added, deleted, model_class, cache_model, items_dict)

        # Check if any of remaining new hashes is in db
        # If it is - we may remove all of the remaining old hashes
        new_leftover = new_hashes[new_index:]
        existing = cache_model.get_by_key_name(new_leftover)
        if any(existing):
            db.delete(cache_model.get_by_key_name(hashes[old_index:]))
        else:
            leftover = hashes[old_index:]

        created = []
        for hsh, obj in zip(new_leftover, existing):
            if not obj:
                created.append(_create_item(hsh, items_dict[hsh], cache_model))
        db.put(created)
    elif not cursor:
        deleted = old_s - new_s
        added = new_s - old_s

        _add_delete(added, deleted, model_class, cache_model, items_dict)

        # Check if we have GDataIndexes for next pages - and delete them
        keys = [key_name.replace(str(page), str(x))
                for x in (page + 1, page + 2)]
        indexes = GDataIndex.get_by_key_name(keys)
        if any(indexes):
            db.delete(indexes)
    else: # not common and cursor
        # All items are different and we still have pages to process.
        # Highly unlikely!
        existing = cache_model.get_by_key_name(new_hashes)

        if any(existing):
            to_delete = cache_model.get_by_key_name(hashes)
            db.delete(to_delete)
        else:
            leftover = hashes[:]

        created = []
        for hsh, obj in zip(new_hashes, existing):
            if not obj:
                created.append(_create_item(hsh, items_dict[hsh], model_class,
                                            cache_model))
        db.put(created)

    if cursor:
        taskqueue.add(url=reverse('new_cache_domain'), params={
            'key_name': request.POST.get('key_name'),
            'page': page + 1,
            'cursor': cursor,
            'hashes': leftover,
        })

    index.hashes = new_hashes
    index.put()
    
    #item_caches = []
    #for item in items:
    #    kw = item._atom_to_kwargs(item._atom)
    #    item_xml = str(item._atom)
    #    hashed = hashlib.sha1(item_xml).hexdigest()
    #    to_set = {}
    #    for key in keys:
    #        to_set[key] = kw[key]
    #    item_cache = cache_model(
    #        key_name=hashed,
    #        **to_set
    #    )
    #    item_caches.append(item_cache)
    #    index.hashes.append(hashed)
    #    index.keys.append(item.key())
    #db.put(item_caches + [index])
    return HttpResponse('ok')


# This view is run as a cron job
def precache_all_domains(request):
    treshold = datetime.datetime.now() - datetime.timedelta(
        seconds=_CACHE_UPDATE_INTERVAL)
    to_update = LastCacheUpdate.all().filter(
        'last_updated <', treshold).order('last_updated').fetch(100)
    for item in to_update:
        mapper, _, domain = item.key().name().partition('-')
        taskqueue.add(url=reverse('precache_domain'), params={
            'domain': domain,
            'mapper': mapper,
        })
    return HttpResponse(str(len(to_update)))


# This view is run as a taskqueue job
def precache_domain(request):
    domain = request.POST['domain']
    mapper = request.POST['mapper']
    if not _MAPPERS_DICT.has_key(mapper):
        return HttpResponse('No such mapper: %s' % mapper)
    apps_domain = AppsDomain.get_by_key_name(domain)
    key_name = '%s-%s' % (mapper, domain)
    last_updated = LastCacheUpdate.get_or_insert(key_name)
    users._set_current_user(apps_domain.admin_email, domain)
    mapper_class = _MAPPERS_DICT[mapper]
    try:
        mapper_class().retrieve_all(use_cache=False)
    except gdata_wrapper.RetryError:
        taskqueue.add(url=request.get_full_path(), params={
            'domain': domain,
            'mapper': mapper,
        })
    last_updated.last_updated = datetime.datetime.now()
    last_updated.put()
    return HttpResponse('ok')


def add_user_to_group(request):
    from crgappspanel import models

    if request.method != 'POST':
        raise Http404

    email = request.POST['email']
    user_name, _, domain = email.rpartition('@')
    group_id = request.POST['group_id']
    hashed = request.POST['hashed']
    as_owner = request.POST['as_owner'] == 'True'

    users._set_current_user(email, domain)
    user = models.GAUser.get_by_key_name(user_name)
    gagroup = models.GAGroup.get_by_key_name(group_id)
    group_owner = models.GAGroupOwner.from_user(user)
    group_member = models.GAGroupMember.from_user(user)

    if gagroup:
        if as_owner:
            gagroup.owners.append(group_owner)
        gagroup.members.append(group_member)
        gagroup.save()

    memcache.incr(hashed, initial_value=0)

    return HttpResponse('ok')

