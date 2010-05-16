import logging
from google.appengine.api import users
from django.conf import settings
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse, get_callable
from django.shortcuts import render_to_response


class Section(object):
    def __init__(self, name, verbose_name, url=None, children=None,
                 parent=None):
        self.name = name
        self.verbose_name = verbose_name
        self.url = url
        self.children = children or []
        self.parent = parent
        self.selected = False

    def __repr__(self):
        return '<Section: %s>' % self.name

    def clone(self):
        children = [child.clone() for child in self.children]
        return Section(
            self.name, self.verbose_name,
            self.url, children, self.parent)


def _get_section(path, sections):
    if isinstance(path, basestring):
        path = path.split('/')
    for section in sections:
        if section.name == path[0]:
            if len(path) == 1:
                return section
            else:
                return _get_section(path[1:], section.children)


def _clone(sections):
    return [section.clone() for section in sections]


def _mark_sections(path, sections, parents=[]):
    for section in sections:
        if section.url == path:
            section.selected = True
            for parent in parents:
                parent.selected = True
        else:
            section.selected = False
        _mark_sections(path, section.children, parents + [section])
    return sections


def _get_selected(sections):
    for section in sections:
        if section.selected:
            return section


def render_with_nav(request, template, ctx={}, extra_nav=None, in_section=None):
    sections = []
    for fun in settings.NAVIGATION:
        fun = get_callable(fun)
        more = fun(request)
        if more:
            sections.extend(more)
    if extra_nav:
        for section in extra_nav:
            if section.parent:
                parent = _get_section(section.parent, sections)
                parent.children.append(section)
            else:
                sections.append(section)
    if in_section:
        path = in_section.split('/')
        for i in range(len(path)):
            _get_section('/'.join(path[:i+1]), sections).selected = True
        ctx['back_link'] = _get_section(in_section, sections).url
    else:
        sections = _mark_sections(request.path, sections)
    ctx['sections'] = sections
    ctx['sel_section'] = _get_selected(sections)
    if ctx['sel_section']:
        ctx['sel_subsection'] = _get_selected(ctx['sel_section'].children)
        if ctx['sel_subsection'] and extra_nav:
            ctx['back_link'] = ctx['sel_subsection'].url
    return render_to_response(
        template, ctx, context_instance=RequestContext(request))
