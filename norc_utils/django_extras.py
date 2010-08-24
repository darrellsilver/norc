
"""Utilities that extend Django functionality."""

from django.db.models import Manager

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

class QuerySetManager(Manager):
    """
    
    This Manager uses a QuerySet class defined within its model and
    will forward attribute requests to it so you only have to
    define custom attributes in one place.
    
    """
    use_for_related_fields = True
    
    def get_query_set(self):
        """Use the model.QuerySet class."""
        return self.model.QuerySet(self.model)
    
    def __getattr__(self, attr, *args):
        """Forward attribute lookup to the QuerySet."""
        return getattr(self.get_query_set(), attr, *args)
    
