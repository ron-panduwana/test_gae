from django.conf.urls.defaults import *


urlpatterns = patterns(
    'crlib.views',
    url(r'^__precache_all_domains/$', 'precache_all_domains'),
    url(r'^__precache_domain/$', 'precache_domain', name='precache_domain'),
    url(r'^__add_user_to_group/$', 'add_user_to_group',
        name='add_user_to_group'),
)

