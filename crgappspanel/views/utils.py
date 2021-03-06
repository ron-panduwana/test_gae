import os

from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext


def get_sortby_asc(request, valid_sortby):
    sortby = request.GET.get('sortby')
    asc = (request.GET.get('asc', 'true') == 'true')
    if not sortby in valid_sortby:
        sortby = None
    return (sortby, asc)


def get_page(request, objs, page_size=30):
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    
    paginator = Paginator(objs, page_size)
    
    try:
        return paginator.page(page)
    except (EmptyPage, InvalidPage):
        return paginator.page(paginator.num_pages)


def qs_wo_page(request):
    qs_obj = request.GET.copy()
    if 'page' in qs_obj:
        del qs_obj['page']
    
    return qs_obj.urlencode()


_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
def secure_random_char(n1, n2, chars=_chars):
    return chars[(256 * n1 + n2) % len(chars)]

def secure_random_chars(howmany, chars=_chars):
    bts = zip(os.urandom(howmany), os.urandom(howmany))
    return ''.join(secure_random_char(ord(b1), ord(b2), chars=chars) for b1, b2 in bts)


def list_attrs(lst, attr, max_len=3, finish='...'):
    real_len = len(lst)
    
    # trimming list if neccessary
    if real_len > max_len:
        lst = lst[:max_len - 1]
        trimmed = True
    else:
        trimmed = False
    
    lst = [getattr(x, attr) for x in lst]
    if trimmed:
        lst.append(finish)
    return lst


def render(request, template, ctx):
    return render_to_response(
        template, ctx, context_instance=RequestContext(request))


def redirect_saved(view, request, *args, **kwargs):
    response = redirect(view, *args, **kwargs)
    request.session['saved'] = True
    return response


def exists_goto(view):
    from functools import wraps
    from gdata.apps.service import AppsForYourDomainException
    
    def error_goto2(f):
        @wraps(f)
        def new_f(request, *args, **kwargs):
            try:
                return f(request, *args, **kwargs)
            except AppsForYourDomainException, ex:
                if ex.reason == 'EntityExists':
                    response = redirect(view)
                    request.session['exists'] = True
                    return response
                else:
                    raise
        return new_f
    return error_goto2


class QueryString(object):
    def __init__(self):
        self.qs = ''
    
    def append(self, key, value):
        if qs:
            qs += '&'
        qs += '%s=%s' % (key, value)
    
    def get(self):
        return ('?%s' % qs) if qs else ''


class QuerySearch(object):
    def __init__(self):
        self.search_by = dict()
        self.filter_attrs = dict()
    
    def add(self, request, query_key, filter_attr):
        value = request.GET.get(query_key)
        if value:
            if query_key:
                self.search_by[query_key] = value
            if filter_attr:
                self.filter_attrs[filter_attr] = value
    
    def is_empty(self):
        return len(self.search_by) == 0 and len(self.filter_attrs) == 0
