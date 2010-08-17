
"""

Contains some functions useful throughout the sqs module as well as the
data definitions for the SQS portions of the web status page.

"""

# import pickle
# from boto.sqs.connection import SQSConnection
# from boto.sqs.message import Message
# 
# from norc.norc_utils import parsing
# from norc.web.data_defs import DataDefinition, DATA_DEFS
# from norc.settings import AWS_ACCESS_KEY_ID as AWS_ID, \
#                           AWS_SECRET_ACCESS_KEY as AWS_KEY
# 
# tasks_def = DATA_DEFS['tasks']
# 
# DataDefinition(
#     key='sqstasks',
#     since_filter=tasks_def.since_filter,
#     order_by=tasks_def.order_by,
#     data={
#         'id': lambda trs, _: trs.id,
#         'task_id': lambda trs, _: str(trs.get_task_id()),
#         'status': lambda trs, _: trs.get_status(),
#         'started': lambda trs, _: trs.date_started,
#         'ended': lambda trs, _: trs.date_ended if trs.date_ended else '-',
#     },
# )
# 
# DataDefinition(
#     key='sqsqueues',
#     retrieve=lambda: SQSConnection(AWS_ID, AWS_KEY).get_all_queues(),
#     data={
#         'id': lambda q, _: q.url.split('/')[-1],
#         'num_items': lambda q, _: q.count(),
#         'timeout': lambda q, _: q.get_timeout(),
#     },
# )
# 