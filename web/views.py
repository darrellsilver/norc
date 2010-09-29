
import os
import datetime

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.db.models.query import QuerySet

from norc import settings
from norc.core import reports
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.web import JSONObjectEncoder, paginate
from norc.norc_utils.formatting import untitle

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html', {
        'sqs': 'norc.sqs' in settings.INSTALLED_APPS,
        'is_superuser': request.user.is_superuser,
        'reports': reports.all,
        'sections': ['daemons', 'queues', 'tasks'],
    })

def get_data(request, content_type, content_id=None, detail_type=None):
    """Retrieves and structures data, then returns it as a JSON object.
    
    Returns a JSON object containing data on given content type.
    If content_id is provided, data on the details of the content_type
    object associated with that id will be returned.  The data is
    filtered by GET parameters in the request.
    
    """
    if not content_type in reports.all:
        raise ValueError("Invalid content type '%s'." % content_type)
    report = reports.all[content_type]
    params = {}
    for k, v in request.GET.iteritems():
        params[str(k)] = v
    params['since'] = parse_since(params.get('since'))
    if detail_type:
        if not detail_type in report.details:
            raise ValueError("Invalid detail type '%s'." % detail_type)
        data_key = detail_type
        data_set = report.details[data_key](content_id, **params)
    else:
        data_key = content_type
        data_set = report(content_id)
    report = reports.all[data_key]
    if type(data_set) == QuerySet:
        data_set = report.since_filter(data_set, params['since'])
        data_set = report.order_by(data_set, params.get('order'))
    page, page_data = paginate(request, data_set)
    json_data = {
        'data': reports.generate(page.object_list, report, params),
        'page': page_data,
    }
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

def get_log(request, content_type, content_id):
    report = reports.all[content_type]
    obj = report.get(content_id)
    header_data = \
        [report.data[untitle(s)](obj, since='all') for s in report.headers]
    local_path = os.path.join(settings.NORC_LOG_DIR, obj.log_path)
    if os.path.isfile(local_path):
        f = open(local_path, 'r')
        log = ''.join(f.readlines())
        f.close()
    else:
        from boto.s3.connection import S3Connection
        from boto.s3.key import Key
        from boto.exception import S3ResponseError
        try:
            c = S3Connection(settings.AWS_ACCESS_KEY_ID,
                settings.AWS_SECRET_ACCESS_KEY)
            key = Key(c.get_bucket(settings.AWS_BUCKET_NAME))
            key.key = 'norc_logs/' + obj.log_path
            log = key.get_contents_as_string()
        except S3ResponseError:
            log = 'Could not retrieve log file from local machine or S3.'
    return render_to_response('log.html', {
        'key': content_type,
        'log': log,
        'headers': report.headers,
        'data': header_data,
    })
