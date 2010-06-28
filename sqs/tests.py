
"""Unit tests for the norc.sqs module."""

import datetime, time
import pickle

from boto.sqs.connection import SQSConnection
from django.test import TestCase

from norc import sqs, utils
from norc.sqs.models import SQSTask
from norc.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

class SQSTaskTest(SQSTask):
    """A test implementation of SQSTask."""
    
    def get_library_path(self):
        return 'norc.sqs.tests.SQSTaskTest'
    
    def get_id(self):
        return 1
    
    def get_queue_name(self):
        return "test_queue"
    
    def has_timeout(self):
        return False
    
    def get_timeout(self):
        return 0
    
    def run(self):
        """Run this SQS Task!
        
        Daemon records success/failure, but any more detail than that is
        left to the internals of the run() implementation.
        
        """
        print "SQSTaskTest has run!!  Great success."
        return True
    

class TestSQSConfig(TestCase):
    """Tests that SQS is properly set up and can push/pop tasks."""
    
    def setUp(self):
        conn = SQSConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        self.queue = conn.lookup('test_queue')
        if not self.queue:
            self.queue = conn.create_queue('test_queue')
        self.queue.clear()
    
    def test_push_task(self):
        # There should be nothing in the test queue.
        utils.wait_until(lambda: self.queue.clear() == 0)
        task = SQSTaskTest(datetime.datetime.utcnow())
        sqs.push_task(task, self.queue)
        utils.wait_until(lambda: self.queue.count() == 1)
    
    def test_pull_task(self):
        utils.wait_until(lambda: self.queue.clear() == 0)
        task = SQSTaskTest(datetime.datetime.utcnow())
        sqs.push_task(task, self.queue)
        utils.wait_until(lambda: self.queue.count() == 1)
        popped = sqs.pop_task(self.queue)
        self.assertNotEqual(popped, None)
        self.assertEqual(task.__class__, popped.__class__)
    
    def tearDown(self):
        self.queue.clear()
    
