from django.utils.translation import ugettext_lazy as _

from crgappspanel.helpers import tables
from crgappspanel.views.utils import get_sortby_asc


#Indicates if the domain is enabled. 
def _get_enabled(x):
    if x.is_enabled:
        return _('Enabled')
    else:
        return _('Disabled')

_DOMAINS_TABLE_COLUMNS = (
    tables.Column(_('Domain'), 'domain', link=True),
    tables.Column(_('Administrator Email'), 'admin_email'),
    tables.Column(_('Status'), 'status', getter=_get_enabled),
)
_DOMAINS_TABLE_ID = _DOMAINS_TABLE_COLUMNS[0]
_DOMAINS_TABLE_WIDTHS = ['%d%%' % x for x in (5, 40, 45, 10)]


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
