"""
scholarships/templatetags/scholarship_extras.py

Custom template filters for the scholarships app.
Load in templates with: {% load scholarship_extras %}
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Allows dictionary lookups with a variable key in templates.
    Usage: {{ my_dict|get_item:variable_key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def subtract(value, arg):
    """Subtract arg from value. Useful for progress calculations."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value
