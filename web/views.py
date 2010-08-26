import datetime

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.conf import settings
from django.db.models.query import QuerySet

# from norc.core import report
# from norc.core.models import NorcDaemonStatus
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.web import JSONObjectEncoder, paginate
# from norc.web.data_defs import DATA_DEFS
from norc.core.reports import REPORTS

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html', {
        'sqs': 'norc.sqs' in settings.INSTALLED_APPS,
        'is_superuser': request.user.is_superuser,
        'reports': REPORTS,
        'sections': ['daemons', 'schedulers'],
    })

def get_data(request, content_type, content_id=None, detail_type=None):
    """Retrieves and structures data, then returns it as a JSON object.
    
    Returns a JSON object containing data on given content type.
    If content_id is provided, data on the details of the content_type
    object associated with that id will be returned.  The data is
    filtered by GET parameters in the request.
    
    """
    if not content_type in REPORTS:
        raise ValueError("Invalid content type '%s'." % content_type)
    report = REPORTS[content_type]
    if detail_type:
        if not detail_type in report.details:
            raise ValueError("Invalid detail type '%s'." % detail_type)
        data_key = detail_type
        data_set = report.details[data_key](content_id)
    else:
        data_key = content_type
        data_set = report(content_id)
    report = REPORTS[data_key]
    kws = {}
    for k, v in request.GET.items():
        kws[str(k)] = v
    kws['since'] = parse_since(kws.get('since'))
    if type(data_set) == QuerySet:
        data_set = report.since_filter(data_set, kws['since'])
        data_set = report.order_by(data_set, kws.get('order'))
    page, page_data = paginate(request, data_set)
    json_data = {'data': [], 'page': page_data}
    for obj in page.object_list:
        obj_data = {}
        for key, func in report.data.iteritems():
            obj_data[key] = func(obj, **kws)
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
