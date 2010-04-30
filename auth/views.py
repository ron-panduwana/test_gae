import array
import base64
import datetime
import hashlib
import logging
import math
import re
import urllib
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.conf import settings
from django.template import RequestContext
from google.appengine.ext import db
from google.appengine.api import memcache, urlfetch
from openid.consumer.discover import OpenIDServiceEndpoint
from openid.consumer.consumer import Consumer, SUCCESS
from openid.store.memstore import MemoryStore
from openid.extensions import ax
from auth.models import AppsDomain
from auth.store import DatastoreStore
from auth.forms import CaptchaForm, DomainSetupForm
from auth import users


HOST_META_URL = 'https://www.google.com/accounts/o8/.well-known/host-meta?%s'
RE_LINK = re.compile(r'Link: <(.*)>')

AX_PREFIX = 'http://axschema.org/'
AX_ATTRS = (
    ('contact/email', 'email'),
    ('namePerson/first', 'firstname'),
    ('namePerson/last', 'lastname'),
)


# TODO: below should be automated
# Certificate data
# Steps required to get this value:
# - get the value of result.content variable from _fetch_xrds
# - extract the value of ds:X509Certificate xml tag
# - split this value to 64-lenght lines
# - enclose it with -----BEGIN CERTIFICATE----- and -----END CERTIFICATE-----
# - save it to a file cert
# - run:
#   openssl x509 -modulus -noout < cert | sed s/Modulus=//
# - or certificate data can also be shown by:
#   openssl x509 -text -in cert
CERT_MODULUS = int(''.join("""
    B0E43C286A80AD5AA3EAF4808106D812FEB67381D3339D11AA53C33A3494230
    EF98101E31472734DAAE07F7673A75D4A476EEC5DB9DCD3D064DA8AE9E6DDA5
    33B6DF69A49DC92F47AC975A44CBA0D501FE6166D4FD2C49A26EDEC34705C1A
    D637EEC9F47F47DDDE7288D3953F56EBBA5BCCBCE8DD549C5A13C8D4A70DEA5
    CEFB
""".split()), 16)
CERT_EXPONENT = 65537


store = DatastoreStore()


def _fetch_host_meta(domain):
    key = 'HOST_META:%s' % domain
    cached_value = memcache.get(key)
    if cached_value is not None:
        return cached_value

    host_meta_url = HOST_META_URL % urllib.urlencode({'hd': domain})
    result = urlfetch.fetch(host_meta_url)
    if result.status_code not in (200, 206):
        return None
    match = RE_LINK.match(result.content)
    if match is None:
        return None

    memcache.set(key, match.group(1))
    return match.group(1)


def _verify_signature(message, signature):
    from gdata.tlslite.utils import PyCrypto_RSAKey
    key = PyCrypto_RSAKey.PyCrypto_RSAKey(CERT_MODULUS, CERT_EXPONENT)
    decoded_sig = base64.b64decode(signature)
    sig_bytes = array.array('B', decoded_sig)
    return key.hashAndVerify(sig_bytes, message)


def _fetch_xrds(domain, url):
    key = 'XRDS:%s' % url
    cached_xrds = memcache.get(key)
    if cached_xrds is not None:
        return cached_xrds

    result = urlfetch.fetch(url)
    if result.status_code not in (200, 206):
        return None

    signature = result.headers.get('signature', '')
    if not _verify_signature(result.content, signature):
        return None

    memcache.set(key, result.content)
    return result.content


def openid_get_domain(request):
    pass


def openid_start(request, domain=None):
    from_ = request.GET.get('from')
    redirect_to = request.GET.get(settings.REDIRECT_FIELD_NAME, '')

    if not domain:
        # We currently only support auth via link from Google Apps
        raise Http404

    is_domain_active = AppsDomain.is_arbitrary_domain_active(domain)
    if not is_domain_active:
        return render_to_response('domain_unlicensed.html', {
            'domain': domain})

    # Perform Google Apps-specific OpenID discovery
    url = _fetch_host_meta(domain)
    if url is None:
        raise Http404

    xrds = _fetch_xrds(domain, url)
    if xrds is None:
        raise Http404

    endpoints = OpenIDServiceEndpoint.fromXRDS(domain, xrds)

    request.session.set_test_cookie()

    request.session[settings.SESSION_LOGIN_INFO_KEY] = {
        'domain': domain,
    }
    consumer = Consumer(request.session, store)

    auth_req = consumer.beginWithoutDiscovery(endpoints[0])

    ax_req = ax.FetchRequest()
    for uri, alias in AX_ATTRS:
        ax_req.add(ax.AttrInfo(
            '%s%s' % (AX_PREFIX, uri), alias=alias, required=True))
    auth_req.addExtension(ax_req)

    return_to = request.build_absolute_uri(reverse('openid_return'))
    if redirect_to:
        # We have to use hashed value of redirect_to, because otherwise the URL
        # is too long and we get invalid data back from Google
        hashed = hashlib.sha1(redirect_to).hexdigest()
        memcache.set(hashed, redirect_to, 60)
        return_to += '?%s' % urllib.urlencode({
            settings.REDIRECT_FIELD_NAME: hashed,
        })
    proto = request.is_secure() and 'https' or 'http'
    redirect_url = auth_req.redirectURL(
        '%s://%s/' % (proto, request.get_host()), return_to, True)

    return HttpResponseRedirect(redirect_url)


def openid_return(request):
    redirect_to = request.GET.get(settings.REDIRECT_FIELD_NAME, '')
    redirect_to = memcache.get(redirect_to)

    consumer = Consumer(request.session, store)
    info = consumer.complete(
        request.GET, request.build_absolute_uri(request.get_full_path()))

    if info.status != SUCCESS:
        request.session.flush()
        return HttpResponse('%s: %s' % (info.status, info.message))

    if request.session.test_cookie_worked():
        request.session.delete_test_cookie()
    else:
        return HttpResponse('You need cookies enabled!')

    session_info = request.session[settings.SESSION_LOGIN_INFO_KEY]

    # Get user email and name
    ax_resp = ax.FetchResponse.fromSuccessResponse(info)
    for uri, alias in AX_ATTRS:
        value = ax_resp.data['%s%s' % (AX_PREFIX, uri)]
        if isinstance(value, list):
            value = value[0]
        session_info[alias] = value
    request.session[settings.SESSION_LOGIN_INFO_KEY] = session_info

    if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL

    return HttpResponseRedirect(redirect_to)


def openid_logout(request):
    redirect_to = request.GET.get(
        settings.REDIRECT_FIELD_NAME, request.META.get('HTTP_REFERER', '/'))
    try:
        request.session.flush()
    except TypeError:
        pass
    return HttpResponseRedirect(redirect_to)


def domain_setup(request, domain, template='domain_setup.html'):
    user = users.get_current_user()
    if user is None:
        return HttpResponseRedirect(
            reverse('openid_start', args=(domain,)) +'?%s' % urllib.urlencode({
                settings.REDIRECT_FIELD_NAME: request.get_full_path(),
                'from': 'google',
            }))
    user_domain = user.email().rpartition('@')[2]
    if user_domain != domain:
        return HttpResponseRedirect(
            reverse('domain_setup', args=(user_domain,)))
    if request.method == 'POST':
        data = request.POST.copy()
        data['domain'] = domain
        if not 'account' in data:
            data['account'] = user.email().rpartition('@')[0]
        form = DomainSetupForm(data)
        if form.is_valid():
            apps_domain = AppsDomain.get_by_key_name(domain)
            if apps_domain is None:
                apps_domain = AppsDomain(
                    key_name=domain,
                    domain=domain,
                )
            apps_domain.admin_email = '%s@%s' % (
                form.cleaned_data['account'], domain)
            apps_domain.admin_password = form.cleaned_data['password']
            apps_domain.put()
            redirect_to = form.cleaned_data['callback']
            if not redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            return HttpResponseRedirect(redirect_to)
        else:
            form.data['captcha'] = form.data['password'] = ''
    else:
        form = DomainSetupForm(initial={
            'callback': request.GET.get('callback', ''),
        })
    ctx = {
        'form': form,
        'domain': domain,
    }
    if not 'other_user' in request.GET:
        ctx['email'] = user.email()
    return render_to_response(
        template, ctx, context_instance=RequestContext(request))


def handle_captcha_challenge(request):
    redirect_to = request.GET.get(settings.REDIRECT_FIELD_NAME, '')
    if request.method == 'POST':
        user = users.get_current_user()
        form = CaptchaForm(request.POST)
        if form.is_valid():
            pass
    else:
        client_login_info = request.session.get(
            settings.SESSION_LOGIN_INFO_KEY)
        if client_login_info:
            initial = {
                'captcha_token': client_login_info.get('captcha_token'),
                'captcha_url': client_login_info.get('captcha_url'),
                'captcha_service': client_login_info.get('service', 'apps'),
                'is_old_api': client_login_info.get('is_old_api', True),
            }
            form = CaptchaForm(initial=initial)
        else:
            form = CaptchaForm()

    ctx = {
        'form': form,
    }
    return render_to_response(
        template, ctx, context_instance=RequestContext(request))


def handle_license_updates(request):
    from auth.licensing import LicensingClient
    client = LicensingClient()
    start_datetime = datetime.datetime.now() - datetime.timedelta(hours=1)
    results = client.get_notifications(start_datetime).entry
    apps_domains = []
    for entry in results:
        domain = entry.content.entity.domain_name.text
        state = entry.content.entity.state.text
        apps_domain = AppsDomain.get_by_key_name(domain)

        if apps_domain is None and state == 'ACTIVE':
            apps_domain = AppsDomain(
                key_name=domain,
                domain=domain)
        elif apps_domain is None or apps_domain.license_state == state:
            continue

        if state == 'UNLICENSED':
            logging.warning('Domain %s uninstalled the app.' % domain)

        apps_domain.license_state = state
        apps_domains.append(apps_domain)
    db.put(apps_domains)
    return HttpResponse(str(len(apps_domains)))

