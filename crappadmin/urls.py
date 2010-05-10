from django.conf.urls.defaults import *


urlpatterns = patterns(
    'crappadmin.views',
    url('domains/$', 'all_domains', name='all_domains'),
)

