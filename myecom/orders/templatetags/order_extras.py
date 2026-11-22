from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def add_days(value, days):
    """
    Add a specified number of days to a date.
    Usage: {{ order.created|add_days:7 }}
    """
    try:
        days = int(days)
        return value + timedelta(days=days)
    except (ValueError, TypeError):
        return value