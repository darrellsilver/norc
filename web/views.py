import datetime, pdb

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.template import Context, Template
from django.core.paginator import Paginator, InvalidPage

# from norc.core.models import *
from norc.core import report
from norc.web import structure
from norc.norc_utils.web import JSONObjectEncoder

def paginate(request, data_set):
    try:
        per_page = int(request.GET.get('per_page', 20))
    except ValueError:
        per_page = 15
    paginator = Paginator(data_set, per_page)
    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    if 0 > page_num > paginator.num_pages:
        page_num = 1
    page = paginator.page(page_num)
    page_data = {
        'next': page.next_page_number() if page.has_next() else 0,
        'prev': page.previous_page_number() if page.has_previous() else 0,
        'start': page.start_index(),
        'end': page.end_index(),
    }
    return page, page_data

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html')

def get_data(request, content_type):
    """Returns a JSON object containing data on daemons.
    
    The data is filtered by GET parameters in the request.
    
    """
    data_set = structure.RETRIEVE[content_type](request.GET);
    page, page_data = paginate(request, data_set)
    data = {content_type: {}, 'page': page_data}
    for obj in page.object_list:
        data[content_type][obj.id] = {}
        for k, f in structure.DATA[content_type].iteritems():
            data[content_type][obj.id][k] = f(obj)
    json = simplejson.dumps(data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")

def get_details(request, content_type, content_id):
    """Gets the details for tasks run by a specific daemon."""
    data = {}
    data_key, data_getter = structure.RETRIEVE_DETAILS[content_type]
    for item in data_getter(content_id):
        data[item.id] = {}
        for k, f in structure.DATA[data_key].iteritems():
            data[item.id][k] = f(item)
    json = simplejson.dumps({data_key: data}, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")
