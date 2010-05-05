# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^i18n/', include('django.conf.urls.i18n')),
)

urlpatterns += patterns('crgappspanel.views',
    url(r'^$', 'general.index', name='index'),
    
    url(r'^groups/list/$', 'groups.groups', name='groups'),
    url(r'^groups/details/(?P<name>[^/]+)/$', 'groups.group_details', name='group-details'),
    url(r'^groups/members/(?P<name>[^/]+)/$', 'groups.group_members', name='group-members'),
    
    url(r'^users/list/$', 'users.users', name='users'),
    url(r'^users/create/$', 'users.user_create', name='user-create'),
    url(r'^users/details/(?P<name>[^/]+)/$', 'users.user_details', name='user-details'),
    url(r'^users/email-settings/(?P<name>[^/]+)/$', 'users.user_email_settings', name='user-email-settings'),
    url(r'^users/filters/(?P<name>[^/]+)/$', 'users.user_email_filters', name='user-email-filters'),
    url(r'^users/aliases/(?P<name>[^/]+)/$', 'users.user_email_aliases', name='user-email-aliases'),
    url(r'^users/suspend/(?P<name>[^/]+)/$', 'users.user_suspend', name='user-suspend'),
    url(r'^users/restore/(?P<name>[^/]+)/$', 'users.user_restore', name='user-restore'),
    url(r'^users/remove/(?P<names>.+)/$', 'users.user_remove', name='user-remove'),
    url(r'^users/remove-nickname/(?P<name>[^/]+)/(?P<nickname>[^/]+)/',
        'users.user_remove_nickname', name='user-remove-nickname'),
    
    url(r'^shared-contacts/list/$', 'shared_contacts.shared_contacts', name='shared-contacts'),
    url(r'^shared-contacts/add/$', 'shared_contacts.shared_contact_add', name='shared-contact-add'),
    url(r'^shared-contacts/details/(?P<name>[^/]+)/$',
        'shared_contacts.shared_contact_details', name='shared-contact-details'),
    url(r'^shared-contacts/remove/(?P<names>.+)/$',
        'shared_contacts.shared_contact_remove', name='shared-contact-remove'),
    url(r'^shared-contacts/remove-email/(?P<name>[^/]+)/(?P<email>[^/]+)/$',
        'shared_contacts.shared_contact_remove_email', name='shared-contact-remove-email'),
    url(r'^shared-contacts/remove-phone/(?P<name>[^/]+)/(?P<phone>[^/]+)/$',
        'shared_contacts.shared_contact_remove_phone', name='shared-contact-remove-phone'),
    
    url(r'^language/$', 'general.language', name='language'),
    url(r'^test/$', 'general.test', name='test'), # TODO remove this test in the future
)


urlpatterns += patterns(
    '',
    url(r'^openid/', include('auth.urls')),
)

