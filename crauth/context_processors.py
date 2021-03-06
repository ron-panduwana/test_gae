import logging
from django.core.urlresolvers import reverse
from crauth import users as _users


DASHBOARD_URL = 'https://www.google.com/a/cpanel/%s/Dashboard'
INBOX_URL = 'https://mail.google.com/a/%s'
CALENDAR_URL = 'https://www.google.com/calendar/hosted/%s'
HELP_URL = """https://sites.google.com/a/cloudreach.co.uk/\
cloudreach-powerpanel-help/help/controlpanel/google-apps"""
ROLES_HELP_URL = """https://sites.google.com/a/cloudreach.co.uk/\
cloudreach-powerpanel-help/help/controlpanel/google-apps/roles/list"""


class PermWrapper(object):
    def __init__(self, user):
        self._user = user

    def __getattr__(self, name):
        return self._user.has_perm(name)


def users(request):
    user = _users.get_current_user()
    if user is None:
        return {
            'login_url': _users.create_login_url(request.get_full_path()),
        }
    domain = user.domain()
    domain_name = domain.domain
    just_logged_in = request.session.pop('just_logged_in', False)
    is_expired = just_logged_in and domain.is_expired()
    if request.path.startswith('/roles/list/'):
        help_url = ROLES_HELP_URL
    else:
        help_url = HELP_URL
    return {
        'auth': {
            'user': user,
            'perms': PermWrapper(user),
            'domain': domain_name,
            'apps_domain': domain,
            'is_on_trial': domain.is_on_trial,
            'expiration_date': domain.expiration_date,
            'is_expired': is_expired,
            'logout_url': _users.create_logout_url(DASHBOARD_URL % domain_name),
            'change_domain_url': reverse('openid_get_domain') + '?force',
            'dashboard_url': DASHBOARD_URL % domain_name,
            'inbox_url': INBOX_URL % domain_name,
            'calendar_url': CALENDAR_URL % domain_name,
            'help_url': help_url,
        }
    }


