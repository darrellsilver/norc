
from django import template

register = template.Library()

@register.filter
def totitle(value):
    return value.replace('_', ' ').title()

