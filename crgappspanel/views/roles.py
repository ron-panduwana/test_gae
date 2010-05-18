from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

from crauth import users
from crauth.decorators import login_required, has_perm
from crauth.models import AppsDomain, Role
from crgappspanel.helpers.misc import ValueWithRemoveLink
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.views.utils import get_sortby_asc, secure_random_chars, \
        redirect_saved, render
from crlib.navigation import render_with_nav


_table_fields = (
    Column(_('Name'), 'name', link=True),
    Column(_('Permissions'), 'permissions',
        getter=lambda x: ','.join(x.permissions)),
)
_table_field_names = tuple(f.name for f in _table_fields)
_table_id = _table_fields[0]
_table_widths = tuple('%d%%' % x for x in (5, 20, 75))


@login_required
def roles(request):
    sortby, asc = get_sortby_asc(request, _table_field_names)
    
    domain = AppsDomain.get_by_key_name(users.get_current_user().domain_name)
    roles = Role.for_domain(domain).fetch(1000)
    
    table = Table(_table_fields, _table_id, sortby=sortby, asc=asc)
    table.sort(roles)
    
    return render_with_nav(request, 'roles_list.html', {
        'table': table.generate(roles, widths=_table_widths, singular='role'),
        'saved': request.session.pop('saved', False),
    })
