import logging
from django.utils.translation import ugettext_lazy as _

from crgappspanel.helpers import tables
from crgappspanel.views.utils import get_sortby_asc


#Indicates if the domain is enabled. 
def _get_enabled(x):
    if x.is_enabled:
        return _('Enabled')
    else:
        return _('Disabled')


def _get_last_login(domain):
    if domain.last_login:
        return u'%s (%s)' % (
            domain.last_login_user,
            domain.last_login.strftime('%Y-%m-%d %H:%M'))
    else:
        return ''


def _get_users_len(domain):
    from crauth import users
    from gdata.apps.adminsettings.service import AdminSettingsService
    users._set_current_user(domain.admin_email, domain.domain)
    user = users.get_current_user()
    if not user:
        return _('No admin credentials')
    service = AdminSettingsService()
    service.domain = domain.domain
    try:
        user.client_login(service)
        return '%s/%s' % (
            service.GetCurrentNumberOfUsers(),
            service.GetMaximumNumberOfUsers())
    except Exception:
        logging.exception(
            'Error while retrieving number of users for %s' % domain.domain)
        return _('Error retrieving information')


def _get_status(domain):
    return domain.status or ''


_DOMAINS_TABLE_COLUMNS = (
    tables.Column(_('Domain'), 'domain', link=True),
    tables.Column(_('Administrator Email'), 'admin_email'),
    tables.Column(_('Status'), 'status', getter=_get_enabled),
    tables.Column(_('Last Login'), 'last_login', getter=_get_last_login),
    tables.Column(_('ClientLogin Status'), 'auth_status', getter=_get_status),
    tables.Column(_('Number of Users'), 'users_len', getter=_get_users_len),
)
_DOMAINS_TABLE_ID = _DOMAINS_TABLE_COLUMNS[0]
_DOMAINS_TABLE_WIDTHS = ['%d%%' % x for x in (5, 20, 15, 10, 20, 15, 15)]


#Returns the table of domains sorted alphabetically
def domains_table(request, domains):
    """Returns the table of domains sorted alphabetically. 
	    :param request: URL request.
        :type request: str
	    :param domains: List of domains.
        :type domains: array
        :returns: Table of domains, sorted alphabetically.
	"""
    sortby, asc = get_sortby_asc(request, [f.name for f in _DOMAINS_TABLE_COLUMNS])
    
    table = tables.Table(_DOMAINS_TABLE_COLUMNS,
        _DOMAINS_TABLE_ID, sortby=sortby, asc=asc)
    return table.generate(
        domains, widths=_DOMAINS_TABLE_WIDTHS, singular='domain',
        delete_link_title=_('Delete domains'), can_change=True)
