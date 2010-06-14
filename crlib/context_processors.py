from google.appengine.api import users


def google(request):
    return {
        'google': {
            'user': users.get_current_user(),
            'is_admin': users.is_current_user_admin(),
        },
    }
