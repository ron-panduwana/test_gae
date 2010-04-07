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
    
    url(r'^$', 'crgappspanel.views.index', name='index'),
    
    url(r'^users/$', 'crgappspanel.views.users', name='users'),
    url(r'^users/create/$', 'crgappspanel.views.user_create', name='user-create'),
    url(r'^users/(?P<name>[^/]+)/details/$', 'crgappspanel.views.user', name='user-details'),
    url(r'^users/(?P<name>[^/]+)/(?P<action>[^/]+)/$', 'crgappspanel.views.user_action', name='user-action'),
    url(r'^users/(?P<name>[^/]+)/(?P<action>[^/]+)/(?P<arg>[^/]+)/$', 'crgappspanel.views.user_action', name='user-action'),
    
    url(r'^groups/$', 'crgappspanel.views.groups', name='groups'),
    
    url(r'^shared-contacts/$', 'crgappspanel.views.shared_contacts', name='shared-contacts'),
    url(r'^shared-contacts/add/$', 'crgappspanel.views.shared_contact_add', name='shared-contact-add'),
    
    url(r'^language/$', 'crgappspanel.views.language', name='language'),
    url(r'^test/$', 'crgappspanel.views.test', name='test'), # TODO remove this test in the future
    
    url(r'^login/$', 'crlib.users.generic_login_view',
        {'template': 'login.html'}),
    url(r'^logout/$', 'crlib.users.generic_logout_view', name='logout'),
    # Example:
    # (r'^foo/', include('foo.urls')),

    # Uncomment this for admin:
#     (r'^admin/', include('django.contrib.admin.urls')),
)
