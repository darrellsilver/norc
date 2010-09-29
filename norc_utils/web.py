import datetime
from django.utils import simplejson
from django.core.paginator import Paginator, InvalidPage

class JSONObjectEncoder(simplejson.JSONEncoder):
    """Handle encoding of complex objects.
    
    The simplejson module doesn't handle the encoding of complex
    objects such as datetime, so we handle it here.
    
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%m/%d/%Y %H:%M:%S")
        try:
            return simplejson.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

def paginate(request, data_set):
    try:
        per_page = int(request.GET.get('per_page', 20))
    except ValueError:
        per_page = 20
    paginator = Paginator(data_set, per_page)
    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    if page_num < 1 or page_num > paginator.num_pages:    
        page_num = 1
    page = paginator.page(page_num)
    page_data = {
        'nextPage': page.next_page_number() if page.has_next() else 0,
        'prevPage': page.previous_page_number() if page.has_previous() else 0,
        'start': page.start_index(),
        'end': page.end_index(),
        'current': page_num,
        'total': paginator.num_pages,
    }
    return page, page_data
