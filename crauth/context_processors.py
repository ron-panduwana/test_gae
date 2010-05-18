from crauth import users as _users


DASHBOARD_URL = 'https://www.google.com/a/cpanel/%s/Dashboard'
INBOX_URL = 'https://mail.google.com/a/%s'
CALENDAR_URL = 'https://www.google.com/calendar/hosted/%s'
HELP_URL = 'http://www.google.com/support/a'


class PermWrapper(object):
    def __init__(self, user):
        self._user = user

    def __getattr__(self, name):
        return self._user.hasperm(name)


def users(request):
    user = _users.get_current_user()
    if user is None:
        return {
            'login_url': _users.create_login_url(request.get_full_path()),
        }
    domain = user.domain().domain
    return {
        'auth': {
            'user': user,
            'perms': PermWrapper(user),
            'domain': domain,
            'logout_url': _users.create_logout_url(DASHBOARD_URL % domain),
            'dashboard_url': DASHBOARD_URL % domain,
            'inbox_url': INBOX_URL % domain,
            'calendar_url': CALENDAR_URL % domain,
            'help_url': HELP_URL,
        }
    }


