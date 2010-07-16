
from django.shortcuts import render_to_response

class StaffOnlyMiddleware(object):
    def process_request(self, request):
        if not request.path.startswith('/admin'):
            if not request.user.is_staff:
                return render_to_response('404.html')
