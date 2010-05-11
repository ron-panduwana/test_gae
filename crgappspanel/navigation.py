from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from crlib.navigation import Section


def base(request):
    return (
        Section('dashboard', _('Dashboard')),
        Section('users', _('Users and Groups'), reverse('users'), (
            Section('groups', _('Groups'), reverse('groups')),
            Section('users', _('Users'), reverse('users')),
        )),
        Section('shared_contacts', _('Shared Contacts'),
                reverse('shared-contacts')),
    )


def user_nav(user):
    parent = 'users/users'
    return (
        Section(
            'details', _('General'), reverse('user-details', args=(user,)),
            parent=parent
        ),
        Section(
            'groups', _('Groups'), reverse('user-groups', args=(user,)),
            parent=parent
        ),
        Section(
            'settings', _('Settings'),
            reverse('user-email-settings', args=(user,)),
            parent=parent
        ),
        Section(
            'filters', _('Filters'),
            reverse('user-email-filters', args=(user,)),
            parent=parent
        ),
        Section(
            'aliases', _('Aliases'),
            reverse('user-email-aliases', args=(user,)),
            parent=parent
        ),
    )


def group_nav(group):
    parent = 'users/groups'
    return (
        Section(
            'details', _('General'), reverse('group-details', args=(group,)),
            parent=parent
        ),
        Section(
            'members', _('Members'), reverse('group-members', args=(group,)),
            parent=parent
        ),
    )

