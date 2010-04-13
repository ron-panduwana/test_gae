import os

from settings import APPS_DOMAIN


def get_sortby_asc(request, valid):
    sortby = request.GET.get('sortby', None)
    asc = (request.GET.get('asc', 'true') == 'true')
    if not sortby in valid:
        sortby = None
    return (sortby, asc)


_password_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
def get_password_char(n1, n2):
    return _password_chars[(256 * n1 + n2) % len(_password_chars)]

def random_password(chars):
    bts = os.urandom(2 * chars)
    return ''.join(get_password_char(ord(b1), ord(b2)) for b1, b2 in zip(bts[:chars], bts[chars:]))


def join_attrs(lst, attr, max_len=3, delim='\n', finish='...'):
    real_len = len(lst)
    
    # trimming list if neccessary
    if real_len > max_len:
        lst = lst[:max_len - 1]
        trimmed = True
    else:
        trimmed = False
    
    s = delim.join([getattr(x, attr) for x in lst])
    if trimmed:
        s += delim
        s += finish
    return s


def ctx(d, section=None, subsection=None, back=False):
    from crgappspanel.sections import SECTIONS
    d['domain'] = APPS_DOMAIN
    d['sections'] = SECTIONS
    if section is not None:
        d['sel_section'] = SECTIONS[section - 1]
        if subsection is not None:
            d['sel_subsection'] = SECTIONS[section - 1]['subsections'][subsection - 1]
        d['back_button'] = back
    return d
