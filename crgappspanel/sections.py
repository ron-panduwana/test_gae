from django.core.urlresolvers import reverse

__all__ = ('SECTIONS')

def section(name, view, subsections=None):
    view = reverse(view) if view else '#'
    return dict(name=name, view=view, subsections=subsections)

SECTIONS = [
    section('Dashboard', None),
    section('Users and groups', 'crgappspanel.views.users', [
        section('Users', 'crgappspanel.views.users'),
        section('Groups', 'crgappspanel.views.groups'),
        section('Settings', None),
        section('Test', 'crgappspanel.views.test'),
    ]),
    section('Domain settings', None),
    section('Advanced tools', None),
    section('Support', None),
]
