from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

from crauth.decorators import login_required, has_perm
from crauth.models import AppsDomain, Role
from crauth import users
from crgappspanel.forms import RoleForm
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


@has_perm('read_role')
def roles(request):
    sortby, asc = get_sortby_asc(request, _table_field_names)
    
    roles = users.get_current_domain().roles().fetch(1000)
    
    table = Table(_table_fields, _table_id, sortby=sortby, asc=asc)
    table.sort(roles)
    
    return render_with_nav(request, 'roles_list.html', {
        'table': table.generate(roles, widths=_table_widths, singular='role'),
        'saved': request.session.pop('saved', False),
    })


@has_perm('add_role')
def role_create(request):
    if request.method == 'POST':
        form = RoleForm(request.POST, auto_id=True)
        if form.is_valid():
            role = form.create(users.get_current_domain())
            role.save()
            return redirect_saved('role-details', request, name=role.name)
    else:
        form = RoleForm(auto_id=True)
    
    return render_with_nav(request, 'role_create.html', {
        'form': form,
    }, in_section='users/roles')


@has_perm('change_role')
def role_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    role = users.get_current_domain().get_role(name)
    if not role:
        return redirect('roles')
    
    if request.method == 'POST':
        form = RoleForm(request.POST, auto_id=True)
        if form.is_valid():
            role = form.populate(role)
            return redirect_saved('role-details', request, name=role.name)
    else:
        initial = dict(name=role.name)
        for perm in role.permissions:
            initial[perm] = True
        form = RoleForm(initial=initial, auto_id=True)
    
    return render_with_nav(request, 'role_details.html', {
        'role': role,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, in_section='users/roles')


@has_perm('change_role')
def role_remove(request, names=None):
    if not names:
        raise ValueError('names = %s' % names)
    
    for name in names.split('/'):
        role = users.get_current_domain().get_role(name)
        if role:
            role.delete()
    
    return redirect_saved('roles', request)
