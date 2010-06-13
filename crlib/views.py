import datetime
import logging
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.conf import settings
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from crauth import users
from crauth.models import AppsDomain
from crlib.models import LastCacheUpdate
from crlib import mappers


_CACHE_UPDATE_INTERVAL = 5 * 60 # 5 minutes


def precache_all_domains(request):
    treshold = datetime.datetime.now() - datetime.timedelta(
        seconds=_CACHE_UPDATE_INTERVAL)
    to_update = LastCacheUpdate.all().filter(
        'last_updated <', treshold).order('last_updated').fetch(100)
    for item in to_update:
        domain = item.key().name()
        taskqueue.add(url=reverse('precache_domain'), params={'domain': domain})
    return HttpResponse(str(len(to_update)))


def precache_domain(request):
    try:
        domain = request.POST['domain']
        logging.warning('domain: %s' % str(domain))
        apps_domain = AppsDomain.get_by_key_name(domain)
        last_updated = LastCacheUpdate.get_by_key_name(domain)
        users._set_current_user(apps_domain.admin_email, domain)
        try:
            mappers.UserEntryMapper().retrieve_all(use_cache=False)
            last_updated.last_updated = datetime.datetime.now()
            last_updated.put()
        except mapper.RetryError:
            taskqueue.add(url=request.get_full_path(), params={'domain': domain})
        return HttpResponse('ok')
    except Exception:
        logging.exception('test')
        raise

