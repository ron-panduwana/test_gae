from django.core.urlresolvers import reverse

__all__ = ('get_sections')

class Section(object):
    def __init__(self, name, view, subsections=None, kwargs=None):
        self.name = name
        self.view = reverse(view, kwargs=kwargs) if view else None
        self.subsections = subsections
        self.selected = False
        

def get_sections(user=False):
    sections = [
        Section('Dashboard', None),
        Section('Users and groups', 'users', [
            Section('Groups', 'groups'),
            Section('Users', 'users'),
            Section('Settings', None),
            Section('Test', 'test'),
        ]),
        Section('Shared contacts', 'shared-contacts'),
        Section('Additional management', None),
        Section('Preferences', None),
    ]
    if user:
        kwargs = dict(name=user)
        sections[1].subsections[1].name = user
        sections[1].subsections[1].subsections = [
            Section('General', 'user-details', kwargs=kwargs),
            Section('Settings', 'user-email-settings', kwargs=kwargs),
            Section('Filters', 'user-email-filters', kwargs=kwargs),
            Section('Aliases', 'user-email-aliases', kwargs=kwargs),
        ]
    return sections
