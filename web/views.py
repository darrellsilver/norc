import datetime

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.template import Context, Template
from django.conf import settings

from norc.core import report
from norc.web import structure
from norc.norc_utils.web import JSONObjectEncoder, paginate
from norc.core.models import NorcDaemonStatus

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html', {
        'sqs': 'norc.sqs' in settings.INSTALLED_APPS,
    })

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
        # Turrible temporary hackage to get SQS stuff on the frontend.
        if data_key == 'tasks':
            d = report.nds(content_id)
            if d.get_daemon_type() == 'SQS':
                data_key = 'sqstasks'
        # End the ugly.
        data_set = data_getter(content_id)
    page, page_data = paginate(request, data_set)
    json_data = {'data': [], 'page': page_data}
    for obj in page.object_list:
        obj_data = {}
        for key, ret_func in structure.DATA[data_key].iteritems():
            obj_data[key] = ret_func(obj, request.GET)
        json_data['data'].append(obj_data)
    json = simplejson.dumps(json_data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")
