"""Bullet markup for HTML pages: the only markup is `**bold**` (see Bullet)."""
import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')


@register.filter
def bold(text):
    return mark_safe(_BOLD_RE.sub(r'<strong>\1</strong>', escape(text)))
