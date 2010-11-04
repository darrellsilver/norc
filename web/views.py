
import os
import datetime

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.db.models.query import QuerySet

from norc import settings
from norc.core import reports
from norc.core.constants import Request
from norc.core.models import Scheduler, Executor
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.web import JSONObjectEncoder, paginate
from norc.norc_utils.formatting import untitle

if settings.BACKUP_SYSTEM == "AmazonS3":
    from norc.norc_utils.aws import get_s3_key

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html', {
        'sqs': 'norc.sqs' in settings.INSTALLED_APPS,
        'is_superuser': request.user.is_superuser,
        'reports': reports.all,
        'sections': settings.STATUS_TABLES,
        "requests": {
            "executors": map(Request.name, Executor.VALID_REQUESTS),
            "schedulers": map(Request.name, Scheduler.VALID_REQUESTS),
        },
    })

def get_counts(request):
    s_count = Scheduler.objects.alive().count()
    json = simplejson.dumps(s_count, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")

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

def control(request, content_type, content_id):
    success = False
    if request.user.is_superuser:
        obj = reports.all[content_type].get(content_id)
        req = request.POST.get('request')
        success = obj.make_request(getattr(Request, req.upper()))
    return http.HttpResponse(simplejson.dumps(success), mimetype="json")

def get_log(request, content_type, content_id):    
    if not content_type in reports.all:
        raise ValueError("Invalid content type '%s'." % content_type)
    report = reports.all[content_type]
    obj = report.get(content_id)
    header_data = \
        [report.data[untitle(s)](obj, since='all') for s in report.headers]
    local_path = os.path.join(settings.NORC_LOG_DIR, obj.log_path)
    if os.path.isfile(local_path):
        f = open(local_path, 'r')
        log = ''.join(f.readlines())
        f.close()
    elif settings.BACKUP_SYSTEM == "AmazonS3":
        try:
            log = get_s3_key("norc_logs/" + obj.log_path)
        except:
            log = "Error retrieving log from S3."
    else:
        log = "Could not retrieve log file from local machine."
    return render_to_response('log.html', {
        'key': content_type,
        'log': log,
        'headers': report.headers,
        'data': header_data,
    })
