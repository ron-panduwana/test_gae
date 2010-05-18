from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

from crauth import users
from crauth.decorators import has_perm
from crgappspanel.forms import GroupForm, GroupMembersForm
from crgappspanel.helpers.misc import ValueWithRemoveLink
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import GAGroup, GAGroupOwner, GAGroupMember
from crgappspanel.views.utils import get_sortby_asc, render, redirect_saved
from crlib.navigation import render_with_nav
from crgappspanel.navigation import group_nav

_table_fields = [
    Column(_('Name'), 'name', link=True),
    Column(_('Email address'), 'email', getter=lambda x: x.id),
    Column(_('Email permission'), 'email_permission'),
]
_table_id = Column(None, 'id', getter=lambda x: x.id.partition('@')[0])
_table_widths = ['%d%%' % x for x in (5, 40, 40, 15)]


@has_perm('read_gagroup')
def groups(request):
    sortby, asc = get_sortby_asc(request, [f.name for f in _table_fields])
    
    groups = GAGroup.all().fetch(1000)
    table = Table(_table_fields, _table_id, sortby=sortby, asc=asc)
    table.sort(groups)
    
    return render_with_nav(request, 'groups_list.html', {
        'table': table.generate(groups, widths=_table_widths, singular='group'),
        'saved': request.session.pop('saved', False),
    })


@has_perm('add_gagroup')
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, auto_id=True)
        if form.is_valid():
            group = form.create()
            group.save()
            return redirect_saved('group-details',
                request, name=group.get_pure_id())
    else:
        form = GroupForm(auto_id=True)
    
    return render_with_nav(request, 'group_create.html', {
        'form': form,
    }, in_section='users/groups')


@has_perm('change_gagroup')
def group_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    domain = users.get_current_user().domain_name
    group = GAGroup.all().filter('id', '%s@%s' % (name, domain)).get()
    if not group:
        return redirect('groups')
    
    if request.method == 'POST':
        form = GroupForm(request.POST, auto_id=True)
        if form.is_valid():
            form.populate(group)
            group.save()
            return redirect_saved('group-details',
                request, name=group.get_pure_id())
    else:
        form = GroupForm(initial={
            'id': group.get_pure_id(),
            'name': group.name,
            'description': group.description,
            'email_permission': group.email_permission,
        }, auto_id=True)
        form.fields['id'].help_text = '@%s' % domain
    
    return render_with_nav(request, 'group_details.html', {
        'group': group,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, extra_nav=group_nav(name))


@has_perm('change_gagroup')
def group_members(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    domain = users.get_current_user().domain_name
    group = GAGroup.all().filter('id', '%s@%s' % (name, domain)).get()
    if not group:
        return redirect('groups')
    
    if request.method == 'POST':
        form = GroupMembersForm(request.POST, auto_id=True)
        if form.is_valid():
            modified = False
            
            owner = form.cleaned_data['owner']
            if owner:
                group.owners.append(GAGroupOwner(email=owner).save())
                group.members.append(GAGroupMember(id=owner).save())
                modified = True
            
            member = form.cleaned_data['member']
            if member:
                group.members.append(GAGroupMember(id=member).save())
                modified = True
            
            if modified:
                group.save()
                return redirect_saved('group-members',
                    request, name=group.get_pure_id())
            else:
                return redirect('group-members', name=group.get_pure_id())
    else:
        form = GroupMembersForm(initial={}, auto_id=True)
    
    def remove_owner_link(group, owner):
        kwargs = dict(name=group.get_pure_id(), owner=owner)
        return reverse('group-remove-owner', kwargs=kwargs)
    def remove_member_link(group, member):
        kwargs = dict(name=group.get_pure_id(), member=member)
        return reverse('group-remove-member', kwargs=kwargs)
    
    owner_emails = [owner.email for owner in group.owners]
    member_emails = [member.id for member in group.members]
    owners = [ValueWithRemoveLink(owner, remove_owner_link(group, owner)) for owner in owner_emails]
    members = [ValueWithRemoveLink(member, remove_member_link(group, member)) for member in member_emails if member not in owner_emails]
    
    return render_with_nav(request, 'group_members.html', {
        'form': form,
        'group': group,
        'owners': owners,
        'members': members,
        'saved': request.session.pop('saved', False),
        'scripts': ['swap-widget'],
    }, extra_nav=group_nav(name))


@has_perm('change_gagroup')
def group_remove(request, names=None):
    if not names:
        ValueError('names = %s' % names)
    
    domain = users.get_current_user().domain_name
    for name in names.split('/'):
        group = GAGroup.all().filter('id', '%s@%s' % (name, domain)).get()
        if group:
            group.delete()
    
    return redirect_saved('groups', request)


@has_perm('change_gagroup')
def group_remove_owner(request, name=None, owner=None):
    if not all((name, owner)):
        raise ValueError('name = %s, owner = %s' % (name, owner))
    
    domain = users.get_current_user().domain_name
    group = GAGroup.all().filter('id', '%s@%s' % (name, domain)).get()
    if not group:
        return redirect('groups')
    
    group.owners = [own for own in group.owners if own.email != owner]
    group.members = [mbm for mbm in group.members if mbm.id != owner]
    group.save()
    
    return redirect_saved('group-members', request, name=group.get_pure_id())


@has_perm('change_gagroup')
def group_remove_member(request, name=None, member=None):
    if not all((name, member)):
        raise ValueError('name = %s, member = %s' % (name, member))
    
    domain = users.get_current_user().domain_name
    group = GAGroup.all().filter('id', '%s@%s' % (name, domain)).get()
    if not group:
        return redirect('groups')
    
    group.members = [mem for mem in group.members if mem.id != member]
    group.save()
    
    return redirect_saved('group-members', request, name=group.get_pure_id())
