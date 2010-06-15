from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from crlib.navigation import Section
from crauth import users


def base(request):
    nav = (
        Section('users', _('Users and Groups'), reverse('users'), (
            Section('groups', _('Groups'), reverse('groups')),
            Section('users', _('Users'), reverse('users')),
        )),
        Section('roles', _('Roles'), reverse('roles')),
        Section('shared_contacts', _('Shared Contacts'),
            reverse('shared-contacts')),
        Section('calendar_resources', _('Calendar Resources'),
            reverse('calendar-resources')),
    )

    if users.is_current_user_admin():
        domain = users.get_current_domain().domain
        domain_setup_url = reverse('domain_setup', args=(domain,))
        return nav + (
            Section(
                'domain_settings', _('Settings'),
                domain_setup_url, (
                    Section(
                        'panel_config', _('Panel Configuration'),
                        domain_setup_url),
                    Section(
                        'installation_instructions', _('Additional Setup'),
                        reverse('installation_instructions', args=(domain,))),
                )),
        )
    else:
        return nav


def user_nav(user):
    parent = 'users/users'
    return (
        Section(
            'details', _('General'), reverse('user-details', args=(user,)),
            parent=parent
        ),
        Section(
            'roles', _('Roles'), reverse('user-roles', args=(user,)),
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

