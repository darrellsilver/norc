
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





from django.contrib import admin

from norc.core import models as core

admin.site.register(core.Resource)
admin.site.register(core.ResourceRegion)
admin.site.register(core.RegionResourceRelationship)
admin.site.register(core.TaskRunStatus)
admin.site.register(core.TaskResourceRelationship)


class ResourceReservationAdmin(admin.ModelAdmin):
    list_display = ['id', 'region', 'resource', 'units_reserved', 'date_reserved']
    ordering = ['region','id']
admin.site.register(core.ResourceReservation, ResourceReservationAdmin)

class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = [core.TaskDependency.__unicode__
        , core.TaskDependency.get_dependency_type, core.TaskDependency.get_status]
admin.site.register(core.TaskDependency, TaskDependencyAdmin)

class JobAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'date_added']
admin.site.register(core.Job, JobAdmin)

class IterationAdmin(admin.ModelAdmin):
    list_display = ['job', core.Iteration.get_id, 'status', 'iteration_type', 'date_started', 'date_ended']
admin.site.register(core.Iteration, IterationAdmin)

class TCIAdmin(admin.ModelAdmin):
    list_display = ['library_name', 'class_name', 'status']
admin.site.register(core.TaskClassImplementation, TCIAdmin)

#

class StartIterationAdmin(admin.ModelAdmin):
    list_display = ['id', 'target_job', 'target_iteration_type', core.StartIteration.get_pretty_schedule, 'allow_simultanious']
admin.site.register(core.StartIteration, StartIterationAdmin)

class RunCommandAdmin(admin.ModelAdmin):
    list_display = ['id', 'cmd', 'timeout', 'nice', core.RunCommand.get_job, 'get_status', 'date_added']
admin.site.register(core.RunCommand, RunCommandAdmin)

# class ScheduledRunCommandAdmin(admin.ModelAdmin):
#     list_display = ['id', 'cmd', 'timeout', 'nice', core.RunCommand.get_job, 'get_status', 'date_added']
# admin.site.register(core.ScheduledRunCommand, ScheduledRunCommandAdmin)

#
