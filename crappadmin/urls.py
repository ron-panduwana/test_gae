from django.conf.urls.defaults import *


urlpatterns = patterns(
    'crappadmin.views',
    url(r'domains/list/$', 'domains', name='domains'),
    url(r'domains/create/$', 'domain_create', name='domain-create'),
    url(r'domains/details/(?P<name>[^/]+)/$', 'domain_details', name='domain-details'),
    url(r'domains/remove/(?P<names>.+)/$', 'domain_remove', name='domain-remove'),
    url(r'tools/$', 'tools', name='tools'),
)
