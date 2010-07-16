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
from crlib import mappers, gdata_wrapper, cache


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


def new_cache_domain(request):
    cache.update_cache(request.POST)
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

