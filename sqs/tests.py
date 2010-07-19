
"""Unit tests for the norc.sqs module."""

import datetime, time
import pickle
import unittest

from boto.sqs.connection import SQSConnection
# from django.test import TestCase

from norc import sqs
from norc.sqs.models import SQSTask
from norc.norc_utils import wait_until
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
    

class TestSQSConfig(unittest.TestCase):
    """Tests that SQS is properly set up and can push/pop tasks."""
    
    def setUp(self):
        self.conn = SQSConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        self.queue = self.conn.lookup('test_queue')
        if not self.queue:
            self.queue = self.conn.create_queue('test_queue', 0)
        wait_until(lambda: self.queue.clear() == 0)
        wait_until(lambda: self.queue.count() == 0)
    
    def test_push_task(self):
        # There should be nothing in the test queue.
        task = SQSTaskTest(datetime.datetime.utcnow())
        sqs.push_task(task, self.queue)
        wait_until(lambda: self.queue.read() != None)
    
    def test_pull_task(self):
        task = SQSTaskTest(datetime.datetime.utcnow())
        sqs.push_task(task, self.queue)
        wait_until(lambda: self.queue.read() != None)
        def try_pop():
            self.popped = sqs.pop_task(self.queue)
            return self.popped != None
        # popped = sqs.pop_task(self.queue)
        wait_until(try_pop)
        self.assertEqual(task.__class__, self.popped.__class__)
    
    def tearDown(self):
        self.queue.clear()
        # wait_until(lambda: self.conn.delete_queue(self.queue))
    
if __name__ == '__main__':
    unittest.main()
