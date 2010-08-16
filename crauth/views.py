import datetime
import hashlib
import logging
import urllib
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.conf import settings
from django.template import RequestContext
from django.template.loader import render_to_string
from google.appengine.ext import db
from google.appengine.api import memcache
from openid.consumer.consumer import Consumer, SUCCESS
from openid.store.memstore import MemoryStore
from openid.extensions import ax
from crauth.models import AppsDomain
from crauth.store import DatastoreStore
from crauth.forms import DomainNameForm, ChooseDomainForm, CaptchaForm, \
        DomainSetupForm
from crauth.ga_openid import discover_google_apps
from crauth import users
from crauth.signals import domain_setup_signal
from crlib.navigation import render_with_nav


SESSION_DOMAINS_KEY = '_domains_set'
AX_PREFIX = 'http://axschema.org/'
AX_ATTRS = (
    ('contact/email', 'email'),
    ('namePerson/first', 'firstname'),
    ('namePerson/last', 'lastname'),
)

store = DatastoreStore()


def openid_get_domain(request, template='get_domain.html'):
    domains = request.session.get(SESSION_DOMAINS_KEY, set())
    if len(domains) == 1 and not request.GET.has_key('force'):
        # We only have one domains in cookies, let's redirect directly to this
        # domain.
        return HttpResponseRedirect(
            reverse('openid_start', args=(domains.pop(),)))
    if domains:
        choices = [(domain, domain) for domain in domains]
        choices.append(
            ('other', _('Other, please specify: www.')),
        )
    with_domains = bool(domains)
    if request.method == 'POST':
        if domains:
            form = ChooseDomainForm(request.POST, choices=choices)
        else:
            form = DomainNameForm(request.POST)
        if form.is_valid():
            domain = form.cleaned_data['domain']
            return HttpResponseRedirect(
                reverse('openid_start', args=(domain,)))
    else:
        if domains:
            form = ChooseDomainForm(choices=choices,
                                    initial={'domain': (domains.pop(), '')})
        else:
            form = DomainNameForm()
    ctx = {
        'form': form,
        'with_domains': with_domains,
    }
    return render_to_response(
        template, ctx, context_instance=RequestContext(request))


def openid_change_domain(request, domain, template='change_domain.html'):
    current_domain = users.get_current_domain()
    if current_domain:
        if current_domain.domain != domain:
            if request.method == 'POST':
                if 'yes' not in request.POST:
                    return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
            else:
                return render_with_nav(request, template, {'domain': domain})
        else:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    return HttpResponseRedirect(reverse('openid_start', args=(domain,)))


def openid_start(request, domain=None):
    from_ = request.GET.get('from')
    redirect_to = request.GET.get(settings.REDIRECT_FIELD_NAME, '')

    if not domain:
        return HttpResponseRedirect(reverse('openid_get_domain'))

    if not AppsDomain.is_arbitrary_domain_active(domain):
        return render_to_response('domain_unlicensed.html', {
            'domain': domain})

    request.session.set_test_cookie()

    request.session[settings.SESSION_LOGIN_INFO_KEY] = {
        'domain': domain,
    }

    consumer = Consumer(request.session, store)
    service = discover_google_apps(domain)
    if service is None:
        raise Http404
    auth_req = consumer.beginWithoutDiscovery(service)

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
        '%s://%s/' % (proto, request.get_host()), return_to, False)

    return HttpResponseRedirect(redirect_url)


def openid_return(request):
    redirect_to = request.GET.get(settings.REDIRECT_FIELD_NAME, '')
    redirect_to = memcache.get(redirect_to)

    consumer = Consumer(request.session, store)
    info = consumer.complete(
        request.GET, request.build_absolute_uri(request.get_full_path()))

    if info.status != SUCCESS:
        request.session.pop(settings.SESSION_LOGIN_INFO_KEY, None)
        return HttpResponse('%s: %s' % (info.status, info.message))

    if request.session.test_cookie_worked():
        request.session.delete_test_cookie()
    else:
        return HttpResponse('You need cookies enabled!')

    session_info = request.session[settings.SESSION_LOGIN_INFO_KEY]
    domains_set = request.session.get(SESSION_DOMAINS_KEY, set())
    domains_set.add(session_info['domain'])
    request.session[SESSION_DOMAINS_KEY] = domains_set

    # Request information about user email and name
    ax_resp = ax.FetchResponse.fromSuccessResponse(info)
    for uri, alias in AX_ATTRS:
        value = ax_resp.data.get('%s%s' % (AX_PREFIX, uri), '')
        if isinstance(value, list):
            value = value[0]
        session_info[alias] = value
    request.session[settings.SESSION_LOGIN_INFO_KEY] = session_info

    if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL

    request.session['just_logged_in'] = True

    return HttpResponseRedirect(redirect_to)


def openid_logout(request):
    redirect_to = request.GET.get(
        settings.REDIRECT_FIELD_NAME, request.META.get('HTTP_REFERER', '/'))
    try:
        request.session.pop(settings.SESSION_LOGIN_INFO_KEY, None)
    except TypeError:
        pass
    return HttpResponseRedirect(redirect_to)


def domain_setup(request, domain, template='domain_setup.html'):
    from gdata.apps.service import AppsService
    token = request.GET.get('token')
    apps_domain = AppsDomain.get_by_key_name(domain)
    if token and token == apps_domain.installation_token:
        user = None
    else:
        token = None
        is_from_google = request.GET.get('from', '') == 'google'
        if is_from_google:
            redirect_to = request.path + '?%s' % urllib.urlencode({
                'callback': request.GET.get('callback', ''),
            })
            return HttpResponseRedirect(
                reverse('openid_start', args=(domain,)) +'?%s' % urllib.urlencode({
                    settings.REDIRECT_FIELD_NAME: redirect_to,
                }))
        elif not users.is_current_user_admin():
            return HttpResponseRedirect(reverse('admin_required'))
        user = users.get_current_user()
    service = AppsService(domain=domain)
    if request.method == 'POST':
        data = request.POST.copy()
        data['domain'] = domain
        if not 'account' in data:
            data['account'] = user.email().rpartition('@')[0]
        if not user:
            user = users.User('%s@%s' % (data['account'], domain), domain)
        form = DomainSetupForm(user, service, data)
        if form.is_valid():
            domain_setup_signal.send(sender=domain)
            redirect_to = form.cleaned_data['callback']
            if not redirect_to and token:
                redirect_to = reverse('installation_instructions',
                                      args=(domain,))
            elif not redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            return HttpResponseRedirect(redirect_to)
        else:
            form.data['captcha'] = form.data['password'] = ''
    else:
        form = DomainSetupForm(user, service, initial={
            'callback': request.GET.get('callback', ''),
        })
    ctx = {
        'form': form,
        'domain': domain,
        'fix': request.GET.has_key('fix'),
    }
    if not token and not 'other_user' in request.GET:
        ctx['email'] = user.email()
    return render_with_nav(request, template, ctx)


OAUTH_SETTINGS_URL = 'https://www.google.com/a/cpanel/%s/ManageOauthClients'
def installation_instructions(request, domain, template='instructions.html'):
    ctx = {
        'app_id': settings.OAUTH_CONSUMER,
        'oauth_settings_url': OAUTH_SETTINGS_URL % domain,
    }
    return render_with_nav(request, template, ctx)


def handle_captcha_challenge(request, template='captcha.html'):
    redirect_to = request.GET.get(settings.REDIRECT_FIELD_NAME, '')
    if request.method == 'POST':
        import pickle
        client_login_info = request.session.get(
            settings.SESSION_LOGIN_INFO_KEY)
        service = pickle.loads(client_login_info['service'])
        user = users.get_current_user()
        form = CaptchaForm(user, service, request.POST)
        if form.is_valid():
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            return HttpResponseRedirect(redirect_to)
    else:
        client_login_info = request.session.get(
            settings.SESSION_LOGIN_INFO_KEY)
        initial = {
            'captcha_token': client_login_info.get('captcha_token'),
            'captcha_url': client_login_info.get('captcha_url'),
        }
        form = CaptchaForm(initial=initial)
    ctx = {
        'form': form,
    }
    return render_to_response(
        template, ctx, context_instance=RequestContext(request))


def handle_license_updates(request):
    from crauth.licensing import LicensingClient
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


def generate_manifest(request):
    abs = lambda x: urllib.unquote(request.build_absolute_uri(x))
    setup_url = reverse('domain_setup', args=('example.com',)).replace(
        'example.com', '${DOMAIN_NAME}') + '?from=google'
    login_url = reverse('openid_start', args=('example.com',)).replace(
        'example.com', '${DOMAIN_NAME}')
    ctx = {
        'setup_url': abs(setup_url),
        'login_url': abs(login_url),
        'realm': abs('/'),
    }
    manifest = render_to_string('manifest.xml', ctx)
    return HttpResponse(manifest, mimetype='text/plain')


def notify_of_expired_domains(request):
    from django.core.mail import mail_admins

    today = datetime.date.today()
    domains = AppsDomain.all().filter('is_on_trial', True).filter(
        'expiration_date <', today).fetch(100)
    domains_list = ''
    for domain in domains:
        if domain.is_active():
            domains_list += '- %s (%s), expired on: %s' % (
                domain.domain, domain.admin_email, domain.expiration_date)
    if domains_list:
        mail_admins(
            'Cloudreach Controlpanel expired domains notification',
            """The following domains' trial period has expired:
            %s
            """ % domains_list)

    return HttpResponse(domains_list)

