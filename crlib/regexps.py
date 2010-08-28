import re
from django.utils.translation import ugettext_lazy as _


RE_DOMAIN = re.compile(r'^(?:[-\w]+\.)+[a-z]{2,6}$')
ERROR_DOMAIN = _('Please enter valid domain name')

# Look at http://www.google.com/support/a/bin/answer.py?answer=33386 for
# description of allowed characters in usernames, first and last names
# and passwords
RE_USERNAME = re.compile(r'^[a-z0-9]([a-z0-9\-_\.\']*[a-z0-9\-_\'])?$',
                         re.IGNORECASE)
ERROR_USERNAME = _(
    'Usernames may contain letters (a-z), numbers (0-9), dashes (-), '
    'underscores (_), periods (.), and apostrophes (\'), and may not '
    'contain an equal sign (=) or brackets (<,>).')
ERROR_NICKNAME = _(
    'Nicknames may contain letters (a-z), numbers (0-9), dashes (-), '
    'underscores (_), periods (.), and apostrophes (\'), and may not '
    'contain an equal sign (=) or brackets (<,>).')

RE_FIRST_LAST_NAME = re.compile(r'^((?!_)[\w\ \-\/\.]){1,40}$',
                                re.UNICODE | re.IGNORECASE)
ERROR_FIRST_LAST_NAME = _(
    'First and last name support unicode/UTF-8 characters, and may '
    'contain spaces, letters (a-z), numbers (0-9), dashes (-), forward '
    'slashes (/), and periods (.), with a maximum of 40 characters.')
