from django.conf.urls.defaults import *


DOMAIN = r'(?P<domain>(?:[-\w]+\.)+[a-z]{2,6})'


urlpatterns = patterns(
    'crauth.views',
    url(r'login/$', 'openid_get_domain', name='openid_get_domain'),
    url(r'login/%s/$' % DOMAIN, 'openid_start', name='openid_start'),
    url(r'return/$', 'openid_return', name='openid_return'),
    url(r'logout/$', 'openid_logout', name='openid_logout'),
    url(r'setup/%s/$' % DOMAIN, 'domain_setup', name='domain_setup'),
    url(r'captcha/$', 'handle_captcha_challenge', name='captcha'),
    url(r'__cron_check_licenses/$', 'handle_license_updates'),
    url(r'__manifest/$', 'generate_manifest'),
)


urlpatterns += patterns(
    'django.views.generic.simple',
    url(r'admin_required/$', 'direct_to_template',
        {'template': 'admin_required.html'}, name='admin_required'),
    url(r'setup_required/$', 'direct_to_template',
        {'template': 'setup_required.html'}, name='setup_required'),
)

