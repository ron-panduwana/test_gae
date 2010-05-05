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
    parts = value.partition('@')
    if any(not part or ' ' in part or ',' in part for part in parts):
        return None
    return dict(username=parts[0], at=parts[1], domain=parts[2])
