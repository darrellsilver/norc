
"""File to contain functions for controlling parts of Norc."""

from datetime import datetime

from norc.core.constants import Status

def handle(obj):
    if not obj.is_alive():
        obj.status = Status.HANDLED
        if hasattr(obj, "ended") and obj.ended == None:
            obj.ended = datetime.utcnow()
        obj.save()
        return True
    else:
        return False
