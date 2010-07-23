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
from crlib.models import GDataIndex
from crlib import cache


def precache_everything(request):
    treshold = datetime.datetime.now() - datetime.timedelta(
        seconds=settings.CACHE_UPDATE_INTERVAL)
    to_update = GDataIndex.all().filter(
        'last_updated <', treshold).filter('last_updated !=', None).order(
            'last_updated').fetch(100)
    for item in to_update:
        key_parts = item.key().name().split(':')
        if len(key_parts) == 3:
            continue
        taskqueue.add(url=reverse('precache_domain_item'), params={
            'key_name': ':'.join(key_parts[:2]),
        })
    return HttpResponse(str(len(to_update)))


def precache_domain_item(request):
    try:
        cache.update_cache(request.POST)
    except Exception:
        logging.exception('wtf')
        raise
    return HttpResponse('ok')


def precache_nicknames(request):
    from crlib.models import GDataIndex, NicknameCache
    domain = request.POST['domain']
    index = GDataIndex.get_by_key_name(request.POST['index'])

    apps_domain = AppsDomain.get_by_key_name(domain)
    users._set_current_user(apps_domain.admin_email, domain)

    all_nicknames = []
    for user in request.POST['users'].split(':'):
        existing = NicknameCache.all().filter('user_name', user).fetch(100)
        existing_names = [nick.nickname for nick in existing]
        nicknames = models.GANickname.all(cached=False).filter(
            'user_name', user).fetch(100)
        names = [nick.nickname for nick in nicknames]

        # Delete unneeded nicknames
        to_delete_names = set(existing_names) - set(names)
        to_delete = []
        for name in to_delete_names:
            to_delete.append(existing[existing_names.index(name)])
        db.delete(to_delete)

        # Nicknames are immutable, so we only have to create the new ones
        to_create_names = set(names) - set(existing_names)
        to_create = []
        for name in to_create_names:
            to_create.append(nicknames[names.index(name)])

        for nickname in to_create:
            all_nicknames.append(NicknameCache.from_model(
                nickname,
                key_name='%s:%s' % (domain, nickname.key()),
                _atom=nickname._atom,
                _gdata_key_name=nickname.key(),
                _domain=domain,
            ))
    db.put(all_nicknames)
    return HttpResponse('ok')


def prepare_indexes(request):
    count = 0
    for domain in AppsDomain.all():
        cache.prepare_indexes(domain.domain)
        count += 1
    return HttpResponse(str(count))


def add_user_to_group(request):
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

