""" Unit tests for the web module.

So far, tests the data retrieval functionality.

"""

from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson as json

# class DataRetrievalTest(TestCase):
#     
#     def setUp(self):
#         init_test_db()
#         self.c = Client()
#         # self.c.login(username='max', password='norc')
#     
#     def test_daemons(self):
#         data = self.c.get('/data/daemons/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "status": "ENDED",
#             "success": 1,
#             "started": "06/07/2010 00:00:00",
#             "region": "TEST_REGION",
#             "pid": 9001,
#             "host": "test.norc.com",
#             "ended": "08/27/2010 00:00:00",
#             "running": 0,
#             "errored": 0,
#             "type": "NORC",
#             "id": 1
#         }])
#     
#     def test_daemon_details(self):
#         data = self.c.get('/data/daemons/1/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "status": "SUCCESS",
#             "task": "RunCommand.1",
#             "started": "07/29/2010 09:30:42",
#             "iteration": 1,
#             "ended": "07/29/2010 16:46:42",
#             "job": "TEST",
#             "id": 1
#         }])
#     
#     def test_jobs(self):
#         data = self.c.get('/data/jobs/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "added": "07/11/2010 12:34:56",
#             "description": "test",
#             "name": "TEST",
#             "id": 1
#         }])
#     
#     def test_jobs_details(self):
#         data = self.c.get('/data/jobs/1/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "status": "",
#             "started": "07/11/2010 13:13:13",
#             "type": "PERSISTENT",
#             "id": 1,
#             "ended": "-"
#         }])
#     
#     def test_iteration_details(self):
#         data = self.c.get('/data/iterations/1/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "status": "SUCCESS",
#             "task": "RunCommand.1",
#             "started": "07/29/2010 09:30:42",
#             "iteration": 1,
#             "ended": "07/29/2010 16:46:42",
#             "job": "TEST",
#             "id": 1
#         }])
