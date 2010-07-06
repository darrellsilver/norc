import datetime
from django.utils import simplejson

class JSONObjectEncoder(simplejson.JSONEncoder):
    """Handle encoding of complex objects.
    
    The simplejson module doesn't handle the encoding of complex
    objects such as datetime, so we handle it here.
    
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return self.encode_datetime(obj)
        return simplejson.JSONEncoder.default(self, obj)
    def encode_datetime(self, dt):
        return dt.strftime("%m/%d/%Y %H:%M:%S")
