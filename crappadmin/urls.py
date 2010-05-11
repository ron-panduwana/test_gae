from django.conf.urls.defaults import *


urlpatterns = patterns(
    'crappadmin.views',
    url('domains/list/$', 'domains', name='domains'),
    url('domains/details/(?P<name>[^/]+)/$', 'domain_details', name='domain-details'),
)
