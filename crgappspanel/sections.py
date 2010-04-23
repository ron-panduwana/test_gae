from django.core.urlresolvers import reverse

__all__ = ('SECTIONS')

class Section(object):
    def __init__(self, name, view, subsections=None):
        self.name = name
        self.view = reverse(view) if view else None
        self.subsections = subsections
        self.selected = False
        

SECTIONS = [
    Section('Dashboard', None),
    Section('Users and groups', 'crgappspanel.views.users.users', [
        Section('Groups', 'crgappspanel.views.groups.groups'),
        Section('Users', 'crgappspanel.views.users.users'),
        Section('Settings', None),
        Section('Test', 'crgappspanel.views.general.test'),
    ]),
    Section('Shared contacts', 'crgappspanel.views.shared_contacts.shared_contacts'),
    Section('Additional management', None),
    Section('Preferences', None),
]
