from django.conf import settings
from django_notify import constants 


def get_level_tags():
    """
    Return the notification level tags.
    
    """
    level_tags = constants.DEFAULT_TAGS.copy()
    level_tags.update(getattr(settings, 'NOTIFICATIONS_TAGS', {}))
    return level_tags
