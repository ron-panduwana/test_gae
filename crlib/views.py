import datetime
import logging
import random
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
from crlib.navigation import render_with_nav
from crlib import cache


def cache_not_ready(request, template='cache_not_ready.html'):
    ctx = {
        'next': request.GET.get(settings.REDIRECT_FIELD_NAME),
    }
    return render_with_nav(request, template, ctx)


def full_precache(request):
    query = GDataIndex.all(keys_only=True)
    if request.method == 'POST':
        query.with_cursor(request.POST['cursor'])

    def txn(key):
        index = GDataIndex.get(key)
        index.full_precache = True
        index.put()

    for key in query.fetch(100):
        db.run_in_transaction(txn, key)

    cursor = query.cursor()
    has_more = bool(GDataIndex.all(keys_only=True).with_cursor(
        cursor).fetch(1))
    if has_more:
        taskqueue.add(url=reverse('full_precache'), params={
            'cursor': cursor,
        })
    return HttpResponse('ok')


def precache_everything(request):
    treshold = datetime.datetime.now() - datetime.timedelta(
        seconds=settings.CACHE_UPDATE_INTERVAL)
    to_update = GDataIndex.all().filter(
        'last_updated <', treshold).filter('last_updated !=', None).order(
            'last_updated').fetch(100)
    counter = 0
    for item in to_update:
        key_parts = item.key().name().split(':')
        if len(key_parts) == 3 or key_parts[1] == 'GANickname':
            continue
        counter += 1
        taskqueue.add(url=reverse('precache_domain_item'), params={
            'key_name': ':'.join(key_parts[:2]),
        }, countdown=random.randint(1, 10))
    return HttpResponse(str(counter))


def precache_domain_item(request):
    from google.appengine.api.urlfetch_errors import DownloadError
    try:
        cache.update_cache(request.POST)
    except DownloadError:
        retry_count = int(request.META.get(
            'HTTP_X_APPENGINE_TASKRETRYCOUNT', 0))
        if retry_count < 3:
            taskqueue.add(url=request.get_full_path(), params=request.POST.copy())
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
    from google.appengine.api.urlfetch_errors import DownloadError
    if request.method != 'POST':
        raise Http404

    email = request.POST['email']
    user_name, _, domain = email.rpartition('@')
    group_id = request.POST['group_id']
    hashed = request.POST['hashed']
    as_owner = request.POST['as_owner'] == 'True'

    users._set_current_user(email, domain)
    service = models.GAGroup._mapper.service
    if as_owner:
        try:
            service.AddOwnerToGroup(email, group_id)
        except DownloadError:
            # It most probably means that the user is already in this group
            pass
    try:
        service.AddMemberToGroup(email, group_id)
    except DownloadError:
        # Same as AddOwnerToGroup
        pass

    memcache.incr(hashed, initial_value=0)

    return HttpResponse('ok')


def gdata_delete(request):
    import base64
    import pickle
    from gdata.client import RequestError
    from crlib.errors import EntityDoesNotExistError

    model_class = request.POST['model']
    model = cache._MODELS_DICT[model_class]
    atom = pickle.loads(base64.b64decode(request.POST['atom']))
    domain = request.POST['domain']
    apps_domain = AppsDomain.get_by_key_name(domain)
    if not apps_domain:
        logging.warning('No such domain: %s' % domain)
        return HttpResponse('not ok')
    
    users._set_current_user(apps_domain.admin_email, domain)

    try:
        model._mapper.delete(atom)
    except EntityDoesNotExistError:
        pass
    except RequestError, e:
        if e.status != 404:
            raise
    return HttpResponse('ok')


def email_settings_update(request):
    from base64 import b64decode
    from pickle import loads
    from gdata.apps.emailsettings.service import EmailSettingsService
    domain = request.POST['domain']
    apps_domain = AppsDomain.get_by_key_name(domain)

    if not apps_domain:
        logging.warning('No such domain: %s' % domain)
        return HttpResponse('not ok')

    users._set_current_user(apps_domain.admin_email, domain)
    user = models.GAUser.get_by_key_name(request.POST['user_name'])
    func = getattr(user.email_settings, request.POST['operation'])

    def unpickle(val):
        return loads(b64decode(val))

    args = request.POST.get('args', ())
    if args:
        args = unpickle(args)
    kwargs = request.POST.get('kwargs', {})
    if kwargs:
        kwargs = unpickle(kwargs)
    kwargs['async'] = False
    func(*args, **kwargs)

    return HttpResponse('ok')

