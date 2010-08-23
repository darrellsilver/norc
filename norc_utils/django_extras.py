
"""Utilities that extend Django functionality."""

# Replaced in Django 1.2 by QuerySet.exists()
def queryset_exists(q):
    """Efficiently tests whether a queryset is empty or not."""
    try:
        q[0]
        return True
    except IndexError:
        return False

def get_object(model, **kwargs):
    """Retrieves a database object of the given class and attributes.
    
    model is the class of the object to find.
    kwargs are the parameters used to find the object.
    If no object is found, returns None.
    
    """
    try:
        model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None
