


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

class ScheduledRunCommandAdmin(admin.ModelAdmin):
    list_display = ['id', 'cmd', 'timeout', 'nice', core.RunCommand.get_job, 'get_status', 'date_added']
admin.site.register(core.ScheduledRunCommand, ScheduledRunCommandAdmin)

#
