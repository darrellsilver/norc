
"""Utilities that extend Django functionality."""

# Replaced in Django 1.2 by QuerySet.exists()
def queryset_exists(q):
    """Efficiently tests whether a queryset is empty or not."""
    try:
        q[0]
        return True
    except IndexError:
        return False
