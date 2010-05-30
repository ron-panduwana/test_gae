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

urlpatterns += patterns('crgappspanel.views.general',
    url(r'^$', 'index', name='index'),
    url(r'^language/$', 'language', name='language'),
    url(r'^test/$', 'test', name='test'), # TODO remove in the future
)

urlpatterns += patterns('crgappspanel.views.users',
    url(r'^users/list/$', 'users', name='users'),
    url(r'^users/create/$', 'user_create', name='user-create'),
    url(r'^users/details/(?P<name>[^/]+)/$',
        'user_details', name='user-details'),
    url(r'^users/roles/(?P<name>[^/]+)/$', 'user_roles', name='user-roles'),
    url(r'^users/groups/(?P<name>[^/]+)/$', 'user_groups', name='user-groups'),
    url(r'^users/email-settings/(?P<name>[^/]+)/$',
        'user_email_settings', name='user-email-settings'),
    url(r'^users/filters/(?P<name>[^/]+)/$',
        'user_email_filters', name='user-email-filters'),
    url(r'^users/aliases/(?P<name>[^/]+)/$',
        'user_email_aliases', name='user-email-aliases'),
    url(r'^users/suspend/(?P<name>[^/]+)/$',
        'user_suspend', name='user-suspend'),
    url(r'^users/restore/(?P<name>[^/]+)/$',
        'user_restore', name='user-restore'),
    url(r'^users/remove/(?P<names>.+)/$', 'user_remove', name='user-remove'),
    url(r'^users/remove-nickname/(?P<name>[^/]+)/(?P<nickname>[^/]+)/$',
        'user_remove_nickname', name='user-remove-nickname'),
    url(r'^users/remove-role/(?P<name>[^/]+)/(?P<role_name>[^/]+)/$',
        'user_remove_role', name='user-remove-role'),
)

urlpatterns += patterns('crgappspanel.views.roles',
    url(r'^roles/list/$', 'roles', name='roles'),
    url(r'^roles/create/$', 'role_create', name='role-create'),
    url(r'^roles/details/(?P<name>[^/]+)/$',
        'role_details', name='role-details'),
    url(r'^roles/remove/(?P<names>.+)/$', 'role_remove', name='role-remove'),
)

urlpatterns += patterns('crgappspanel.views.groups',
    url(r'^groups/list/$', 'groups', name='groups'),
    url(r'^groups/create/$', 'group_create', name='group-create'),
    url(r'^groups/details/(?P<name>[^/]+)/$',
        'group_details', name='group-details'),
    url(r'^groups/members/(?P<name>[^/]+)/$',
        'group_members', name='group-members'),
    url(r'^groups/remove/(?P<names>.+)/$', 'group_remove', name='group-remove'),
    url(r'^groups/remove-owner/(?P<name>[^/]+)/(?P<owner>[^/]+)/$',
        'group_remove_owner', name='group-remove-owner'),
    url(r'^groups/remove-member/(?P<name>[^/]+)/(?P<member>[^/]+)/$',
        'group_remove_member', name='group-remove-member'),
)

urlpatterns += patterns('crgappspanel.views.shared_contacts',
    url(r'^shared-contacts/list/$', 'shared_contacts', name='shared-contacts'),
    url(r'^shared-contacts/add/$',
        'shared_contact_add', name='shared-contact-add'),
    url(r'^shared-contacts/details/(?P<name>[^/]+)/$',
        'shared_contact_details', name='shared-contact-details'),
    url(r'^shared-contacts/remove/(?P<names>.+)/$',
        'shared_contact_remove', name='shared-contact-remove'),
    url(r'^shared-contacts/remove-email/(?P<name>[^/]+)/(?P<email>[^/]+)/$',
        'shared_contact_remove_email', name='shared-contact-remove-email'),
    url(r'^shared-contacts/remove-phone/(?P<name>[^/]+)/(?P<phone>[^/]+)/$',
        'shared_contact_remove_phone', name='shared-contact-remove-phone'),
)

urlpatterns += patterns('crgappspanel.views.calendar_resources',
    url(r'^calendar-resources/list/$',
        'calendar_resources', name='calendar-resources'),
    url(r'^calendar-resources/add/$',
        'calendar_resource_add', name='calendar-resource-add'),
    url(r'^calendar-resources/details/(?P<id>[^/]+)/$',
        'calendar_resource_details', name='calendar-resource-details'),
    url(r'^calendar-resources/remove/(?P<ids>.+)/$',
        'calendar_resource_remove', name='calendar-resource-remove'),
)


urlpatterns += patterns('',
    url(r'^openid/', include('crauth.urls')),
    url(r'^appadmin/', include('crappadmin.urls')),
)

