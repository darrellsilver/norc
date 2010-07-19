import datetime

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.template import Context, Template

# from norc.core.models import *
from norc.core import report
from norc.web import structure
from norc.norc_utils.web import JSONObjectEncoder, paginate

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html')

def get_data(request, content_type, content_id=None):
    """Retrieves and structures data, then returns it as a JSON object.
    
    Returns a JSON object containing data on given content type.
    If content_id is provided, data on the details of the content_type
    object associated with that id will be returned.  The data is
    filtered by GET parameters in the request.
    
    """
    if content_id == None:
        data_key = content_type
        data_set = structure.RETRIEVE[content_type](request.GET)
    else:
        data_key, data_getter = structure.RETRIEVE_DETAILS[content_type]
        data_set = data_getter(content_id)
    page, page_data = paginate(request, data_set)
    data = {data_key: {}, 'page': page_data}
    for obj in page.object_list:
        data[data_key][obj.id] = {}
        for k, f in structure.DATA[data_key].iteritems():
            data[data_key][obj.id][k] = f(obj, request.GET)
    json = simplejson.dumps(data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")
