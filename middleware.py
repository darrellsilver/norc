import traceback
from django.http import HttpResponseServerError
from django.template.loader import render_to_string
from django.shortcuts import render_to_response

class StaffOnlyMiddleware(object):
    def process_request(self, request):
        if not request.path.startswith('/admin'):
            if not request.user.is_staff:
                return render_to_response('404.html')

class ErrorHandlingMiddleware(object):
    def process_exception(self, request, exception):
        if request.is_ajax():
            return HttpResponseServerError(traceback.format_exc(),
                content_type='text/plain')
