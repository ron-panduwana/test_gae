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
    url(r'^$', 'index', name='index'),
    url(r'^groups/list/$', 'groups', name='groups'),
    
    url(r'^users/list/$', 'users', name='users'),
    url(r'^users/create/$', 'user_create', name='user-create'),
    url(r'^users/details/(?P<name>[^/]+)/$', 'user_details', name='user-details'),
    url(r'^users/suspend/(?P<name>[^/]+)/$', 'user_suspend', name='user-suspend'),
    url(r'^users/restore/(?P<name>[^/]+)/$', 'user_restore', name='user-restore'),
    url(r'^users/remove/(?P<names>.+)/$', 'user_remove', name='user-remove'),
    url(r'^users/remove-nickname/(?P<name>[^/]+)/(?P<nickname>[^/]+)/', 'user_remove_nickname', name='user-remove-nickname'),
    
    url(r'^shared-contacts/list/$', 'shared_contacts', name='shared-contacts'),
    url(r'^shared-contacts/add/$', 'shared_contact_add', name='shared-contact-add'),
    url(r'^shared-contacts/details/(?P<name>[^/]+)/$', 'shared_contact_details', name='shared-contact-details'),
    url(r'^shared-contacts/remove/(?P<names>.+)/$', 'shared_contact_remove', name='shared-contact-remove'),
    
    url(r'^language/$', 'language', name='language'),
    url(r'^test/$', 'test', name='test'), # TODO remove this test in the future
)

urlpatterns += patterns('crlib.users',
    url(r'^login/$', 'generic_login_view', {'template': 'login.html'}),
    url(r'^logout/$', 'generic_logout_view', name='logout'),
)
