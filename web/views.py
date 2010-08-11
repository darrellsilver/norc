import datetime

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.conf import settings
from django.db.models.query import QuerySet

from norc.core import report
from norc.core.models import NorcDaemonStatus
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.web import JSONObjectEncoder, paginate
from norc.web.data_defs import DATA_DEFS

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html', {
        'sqs': 'norc.sqs' in settings.INSTALLED_APPS,
        'is_superuser': request.user.is_superuser,
    })

def get_data(request, content_type, content_id=None):
    """Retrieves and structures data, then returns it as a JSON object.
    
    Returns a JSON object containing data on given content type.
    If content_id is provided, data on the details of the content_type
    object associated with that id will be returned.  The data is
    filtered by GET parameters in the request.
    
    """
    ddef = DATA_DEFS[content_type]
    if not ddef: return
    if content_id == None:
        data_key = ddef.key
        data_set = ddef.retrieve()
    else:
        data_key = ddef.detail_key
        # Turrible temporary hackage to get SQS stuff on the frontend.
        if content_type == 'daemons' and data_key == 'tasks':
            d = report.nds(content_id)
            if d.get_daemon_type() == 'SQS':
                data_key = 'sqstasks'
        # End the ugly.
        data_set = ddef.details(content_id, request.GET)
    ddef = DATA_DEFS[data_key]
    if 'since' in request.GET and type(data_set) == QuerySet:
        since_date = parse_since(request.GET['since'])
        if since_date and hasattr(ddef, 'since_filter'):
            data_set = ddef.since_filter(data_set, since_date)
    if hasattr(ddef, 'order_by'):
        data_set = ddef.order_by(data_set, request.GET.get('order'))
    page, page_data = paginate(request, data_set)
    json_data = {'data': [], 'page': page_data}
    for obj in page.object_list:
        obj_data = {}
        for key, ret_func in ddef.data.iteritems():
            obj_data[key] = ret_func(obj, request.GET)
        json_data['data'].append(obj_data)
    json = simplejson.dumps(json_data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")

daemon_control = dict(
    kill=lambda d: d.set_status(NorcDaemonStatus.STATUS_KILLREQUESTED),
    stop=lambda d: d.set_status(NorcDaemonStatus.STATUS_STOPREQUESTED),
    pause=lambda d: d.set_status(NorcDaemonStatus.STATUS_PAUSEREQUESTED),
    delete=lambda d: d.set_status(NorcDaemonStatus.STATUS_DELETED),
    salvage=lambda d: d.set_status(NorcDaemonStatus.STATUS_RUNNING),
)

requests = ['kill', 'stop', 'pause']
force = ['delete', 'salvage']
allowed_status_changes = {
    'RUNNING': ['kill', 'stop', 'pause', 'delete'],
    'STARTING': ['delete'],
    'RUNNING': requests,
    'PAUSED': ['kill', 'stop', 'delete', 'salvage'],
    'PAUSEREQUESTED': force,
    'STOPREQUESTED': force,
    'KILLREQUESTED': force,
    'BEING_STOPPED': force,
    'BEING_KILLED': force,
}

def control(request, content_key, content_id):
    executed = False
    if content_key == 'daemon' and request.user.is_superuser:
        daemon = report.nds(content_id)
        do = request.POST.get('do')
        if do and do in allowed_status_changes.get(daemon.status, []):
            daemon_control[do](daemon)
            executed = True
    return http.HttpResponse(simplejson.dumps(executed), mimetype="json")
