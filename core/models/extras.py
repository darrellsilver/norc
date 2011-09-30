
from django.db.models import Model, CharField

class Revision(Model):
    """Represents a code revision."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_revision'
    
    info = CharField(max_length=64, unique=True)
    
    @staticmethod
    def create(info):
        return Revision.objects.create(info=info)
    
    def __str__(self):
        return '<Revision %s>' % self.info
    
