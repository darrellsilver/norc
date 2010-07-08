
#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#


from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)$', admin.site.root),
    (r'^$', 'norc.web.views.index'),
    (r'^data/(\w+)/$', 'norc.web.views.get_data'),
    (r'^data/(\w+)/(\w+)/$', 'norc.web.views.get_details'),
    # (r'^daemons/$', 'norc.web.views.get_daemons'),
    # (r'^daemons/(\d+)/$', 'norc.web.views.daemon_details'),
    # (r'^jobs/$', 'norc.web.views.get_jobs'),
    # (r'^jobs/(.+)/$', 'norc.web.views.job_details'),
    # (r'^daemon/details/$', 'norc.web.views.daemon_details'),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root' : '/usr/local/norc/static/'}),
    # (r'^sandbox(.*)$', 'norc.web.views.sandbox'),
)
