
import os

from django.conf.urls.defaults import *
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from norc.settings import MEDIA_ROOT

urlpatterns = patterns('',
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)$', admin.site.root),
    (r'^$', 'norc.web.views.index'),
    (r'^data/counts/$', 'norc.web.views.get_counts'),
    (r'^data/(\w+)/$', 'norc.web.views.get_data'),
    (r'^data/(\w+)/(\w+)/$', 'norc.web.views.get_data'),
    (r'^data/(\w+)/(\w+)/(\w+)/$', 'norc.web.views.get_data'),
    (r'^control/(\w+)/(\w+)/$', 'norc.web.views.control'),
    (r'^logs/(\w+)/(\w+)/$', 'norc.web.views.get_log'),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': MEDIA_ROOT}),
)
