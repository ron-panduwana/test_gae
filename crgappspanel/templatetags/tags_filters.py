from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
def iterable(value):
    if isinstance(value, (list, tuple)):
        return value
    return (value,)


@register.filter
@stringfilter
def email_partition(value):
    idx = value.find('@')
    if idx == -1:
        return None
    return dict(username=value[:idx], at=value[idx], domain=value[idx+1:])
