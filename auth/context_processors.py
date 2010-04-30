from auth import users as _users


def users(request):
    user = _users.get_current_user()
    if user is None:
        return {
            'login_url': _users.create_login_url(request.get_full_path()),
        }
    return {
        'user': user,
        'logout_url': _users.create_logout_url(user.domain().dashboard_url()),
    }
