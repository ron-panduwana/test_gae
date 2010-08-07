from django.conf.urls.defaults import *


urlpatterns = patterns(
    'crlib.views',
    url(r'^app_not_ready/$', 'cache_not_ready', name='cache_not_ready'),
    url(r'^__add_user_to_group/$', 'add_user_to_group',
        name='add_user_to_group'),
    url(r'^__gdata_delete/$', 'gdata_delete', name='gdata_delete'),
    url(r'^__precache_everything/$', 'precache_everything',
        name='precache_everything'),
    url(r'^__precache_domain_item/$', 'precache_domain_item',
        name='precache_domain_item'),
    url(r'^__prepare_indexes/$', 'prepare_indexes'),
    url(r'^__precache_nicknames/$', 'precache_nicknames',
        name='precache_nicknames'),
    url(r'^__email_settings_update/$', 'email_settings_update',
        name='email_settings_update'),
)

