
from django.contrib import admin

from norc.core import models

class ExecutorAdmin(admin.ModelAdmin):
    list_display = ['id', 'host', 'pid', 'status', 'request', 
        'heartbeat', 'started', 'ended', 'queue', 'concurrent']

admin.site.register(models.Executor, ExecutorAdmin)

class DBQueueAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'count_']
    
    def count_(self, dbq):
        return dbq.count()
    count_.short_description = "# Enqueued"

admin.site.register(models.DBQueue, DBQueueAdmin)

class DBQueueItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'dbqueue', 'item', 'enqueued']

admin.site.register(models.DBQueueItem, DBQueueItemAdmin)

class QueueGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'count_']
    
    def count_(self, qg):
        return qg.count()
    count_.short_description = "# Enqueued"

admin.site.register(models.QueueGroup, QueueGroupAdmin)

class QueueGroupItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'queue', 'priority']

admin.site.register(models.QueueGroupItem, QueueGroupItemAdmin)

class JobAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 
        'timeout', 'date_added']

    def timeout_(self, j):
        return j.timeout
    timeout_.short_description = "Timeout (secs)"

admin.site.register(models.Job, JobAdmin)

class CommandTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 
        'command', 'nice',
        'timeout', 'date_added']
    
    def timeout_(self, j):
        return j.timeout
    timeout_.short_description = "Timeout (secs)"

admin.site.register(models.CommandTask, CommandTaskAdmin)

class SchedulerAdmin(admin.ModelAdmin):
    list_display = ['id', 'host', 'heartbeat', 'is_alive']

admin.site.register(models.Scheduler, SchedulerAdmin)

class CronScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'queue', 'repetitions', 
        'remaining', 'scheduler', 'make_up', 'base', 'encoding']

admin.site.register(models.CronSchedule, CronScheduleAdmin)

class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'queue', 'repetitions', 
        'remaining', 'scheduler', 'make_up', 'next', 'period']

admin.site.register(models.Schedule, ScheduleAdmin)

