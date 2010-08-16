from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

from crauth import users
from crauth.decorators import has_perm
from crgappspanel.forms import GroupForm, GroupMembersForm
from crgappspanel.helpers.misc import ValueWithRemoveLink
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.helpers.paginator import Paginator
from crgappspanel.models import Preferences, GAGroup, GAGroupOwner, \
        GAGroupMember
from crgappspanel.views.utils import get_sortby_asc, get_page, qs_wo_page, \
        render, redirect_saved
from crgappspanel.navigation import group_nav
from crlib.navigation import render_with_nav
from crlib import errors

_table_fields = (
    Column(_('Name'), 'name', link=True),
    Column(_('Email address'), 'id', getter=lambda x: x.id),
    Column(_('Email permission'), 'email_permission', sortable=False),
)
_table_id = Column(None, 'id', getter=lambda x: x.id.partition('@')[0])
_table_widths = ['%d%%' % x for x in (5, 40, 40, 15)]


@has_perm('read_gagroup')
def groups(request):
    per_page = Preferences.for_current_user().items_per_page
    paginator = Paginator(GAGroup, request, (
        'id', 'name',
    ), per_page)

    table = Table(_table_fields, _table_id)
    
    delete_link_title = _('Delete groups')
    return render_with_nav(request, 'groups_list.html', {
        'table': table.generate_paginator(
            paginator, widths=_table_widths,
            delete_link_title=delete_link_title,
            can_change=users.get_current_user().has_perm('change_gagroup')),
        'saved': request.session.pop('saved', False),
        'delete_question': _('Are you sure you want to delete selected '
                             'groups?'),
        'delete_link_title': delete_link_title,
    }, help_url='groups/list')


@has_perm('add_gagroup')
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, auto_id=True)
        if form.is_valid():
            group = form.create(users.get_current_domain().domain)
            try:
                group.save()
                return redirect_saved('group-details',
                    request, name=group.get_pure_id())
            except errors.EntityExistsError:
                form.add_error(
                    'id', _('User or group with this name already exists.'))
    else:
        form = GroupForm(auto_id=True)
    
    form.fields['id'].help_text = '@%s' % users.get_current_user().domain_name
    return render_with_nav(request, 'group_create.html', {
        'form': form,
    }, in_section='users/groups', help_url='groups/create')


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
    }, extra_nav=group_nav(name), help_url='groups/details')


@has_perm('change_gagroup')
def group_members(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    domain = users.get_current_user().domain_name
    group = GAGroup.get_by_key_name('%s@%s' % (name, domain))
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
    
    suggestions = set()
    
    current_user = users.get_current_user()
    domain_name = current_user.domain_name
    
    if current_user.has_perm('read_gauser'):
        from crgappspanel.models import GAUser, GANickname
        for user in GAUser.all().fetch(1000):
            suggestions.add('%s@%s' % (user.user_name, domain_name))
        for nick in GANickname.all().fetch(1000):
            suggestions.add('%s@%s' % (nick.nickname, domain_name))
    
    if current_user.has_perm('read_sharedcontact'):
        from crgappspanel.models import SharedContact
        for contact in SharedContact.all().fetch(1000):
            for email in contact.emails:
                if email.address:
                    suggestions.add(email.address)
    
    suggestions = list(suggestions)
    suggestions.sort()
    
    return render_with_nav(request, 'group_members.html', {
        'form': form,
        'group': group,
        'owners': owners,
        'members': members,
        'suggestions': suggestions,
        'saved': request.session.pop('saved', False),
    }, extra_nav=group_nav(name), help_url='groups/members')


@has_perm('change_gagroup')
def group_remove(request, names=None):
    if not names:
        ValueError('names = %s' % names)
    
    domain = users.get_current_user().domain_name
    for name in names.split('/'):
        group = GAGroup.get_by_key_name('%s@%s' % (name, domain))
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
