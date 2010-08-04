# 
# """External modules should access Norc data using these functions.
# 
# The main benefit currently is to prevent the occurence of a try block
# everywhere data is needed, and to reduce the amount of code needed for
# retrievals using consistent attributes.  Additionally, it prevents
# external modules from having to query core classes directly.
# 
# """
# 
# from norc.core.models import *
# 
# DAEMON_STATUS_DICT = {}
# DAEMON_STATUS_DICT['running'] = [NorcDaemonStatus.STATUS_RUNNING]
# DAEMON_STATUS_DICT['active'] = [NorcDaemonStatus.STATUS_STARTING,
#                                 NorcDaemonStatus.STATUS_RUNNING,
#                                 NorcDaemonStatus.STATUS_PAUSEREQUESTED,
#                                 NorcDaemonStatus.STATUS_STOPREQUESTED,
#                                 NorcDaemonStatus.STATUS_KILLREQUESTED,
#                                 NorcDaemonStatus.STATUS_PAUSED,
#                                 NorcDaemonStatus.STATUS_STOPINPROGRESS,
#                                 NorcDaemonStatus.STATUS_KILLINPROGRESS]
# DAEMON_STATUS_DICT['errored'] = [NorcDaemonStatus.STATUS_ERROR]
# DAEMON_STATUS_DICT['interesting'] = []
# DAEMON_STATUS_DICT['interesting'].extend(DAEMON_STATUS_DICT['active'])
# DAEMON_STATUS_DICT['interesting'].extend(DAEMON_STATUS_DICT['errored'])
# DAEMON_STATUS_DICT['all'] = NorcDaemonStatus.ALL_STATUSES
# 
# def get_object(class_, **kwargs):
#     """Retrieves a database object of the given class and attributes.
#     
#     class_ is the class of the object to find.
#     kwargs are the parameters used to find the object.get_daemon_status
#     If no object is found, returns None.
#     
#     """
#     try:
#         return class_.objects.get(**kwargs)
#     except class_.DoesNotExist, dne:
#         return None
# 
# def job(name):
#     """Retrieves the Job with the given name, or None."""
#     return get_object(Job, name=name)
# 
# def task(class_, id):
#     """Retrieves the task of type class_ and with the given ID, or None."""
#     return get_object(class_, id=id)
# 
# def region(name):
#     """Retrieves the ResourceRegion with the given name, or None."""
#     return get_object(ResourceRegion, name=name)
# 
# def iteration(id):
#     """Retrieves the Iteration with the given ID, or None."""
#     return get_object(Iteration, id=id)
# 
# def nds(id):
#     """Retrieves the NorcDaemonStatus with the given ID, or None."""
#     return get_object(NorcDaemonStatus, id=id)
# 
# def jobs():
#     return Job.objects.all()
# 
# def ndss(since_date=None, status_filter='all'):
#     """Retrieve NorcDaemonStatuses.
#     
#     Gets all NDSs that have ended since the given date or are still
#     running and match the given status filter.
#     
#     """
#     nds_query = NorcDaemonStatus.objects.all()
#     if since_date != None:
#         # Exclude lte instead of filter gte to retain running daemons.
#         nds_query = nds_query.exclude(date_ended__lte=since_date)
#     if status_filter != 'all' and status_filter in DAEMON_STATUS_DICT:
#         include_statuses = DAEMON_STATUS_DICT[status_filter.lower()]
#         nds_query = nds_query.filter(status__in=include_statuses)
#     return nds_query
# 
# def iterations(jid):
#     return Iteration.objects.filter(job__id=jid)
# 
# def tasks_from_iter(iid):
#     return TaskRunStatus.objects.filter(iteration__id=iid)
# 
# def trss(nds, status_filter='all', since_date=None):
#     """A hack fix so we can get the statuses for the proper daemon type."""
#     status_filter = status_filter.lower()
#     if nds.get_daemon_type() == 'NORC':
#         task_statuses = nds.taskrunstatus_set.all()
#     else:
#         task_statuses = nds.sqstaskrunstatus_set.all()
#     status_filter = status_filter.lower()
#     TRS_CATS = TaskRunStatus.STATUS_CATEGORIES
#     if not since_date == None:
#         task_statuses = task_statuses.exclude(date_ended__lt=since_date)
#     if status_filter != 'all' and status_filter in TRS_CATS:
#         only_statuses = TRS_CATS[status_filter]
#         task_statuses = task_statuses.filter(status__in=only_statuses)
#     return task_statuses
# 
# # DEPR
# # def get_task_statuses(status_filter='all'):
# #     if status_filter == 'all':
# #         TaskRunStatus.objects.all()
# #     else:
# #         include_statuses = TASK_STATUS_DICT[status_filter.lower()]
# #         return TaskRunStatus.objects.filter(status__in=include_statuses)
# 
