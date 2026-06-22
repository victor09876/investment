from django import template

register = template.Library()


@register.filter
def getitem(d, key):
    """Get item from dict using string key (for KYC answers dict)."""
    if d is None:
        return None
    return d.get(str(key))


@register.filter
def getattr(obj, attr):
    """Get attribute dynamically from an object."""
    try:
        return __builtins__['getattr'](obj, attr, None) if isinstance(__builtins__, dict) else __import__('builtins').getattr(obj, attr, None)
    except Exception:
        return None


@register.filter
def split(value, sep=','):
    """Split a string by separator."""
    if not value:
        return []
    return [item.strip() for item in value.split(sep)]
