
from django.db.models import Model, CharField

class Revision(Model):
    """Represents a code revision."""
    
    class Meta:
        app_label = 'core'
    
    info = CharField(max_length=64, unique=True)
    
    def __str__(self):
        return "Revision [%s]" % self.info
    
