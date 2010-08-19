
"""Unit tests for the norc.sqs module."""

from django.test import TestCase

from norc.sqs.models import SQSQueue
from norc.norc_utils import wait_until

class SQSQueueTest(TestCase):
    """Tests the ability to push and pop from an SQSQueue."""
    
    def setUp(self):
        self.queue = SQSQueue.objects.create(name='test')
        self.queue.queue.clear()
        # wait_until(lambda: self.queue.queue.count() == 0)
    
    def test_push_pop(self):
        self.queue.push(self.queue)
        self.q = None
        def get_item():
            self.q = self.queue.pop()
            return self.q != None
        wait_until(get_item)
        self.assertEqual(self.queue, self.q)
    
    def tearDown(self):
        pass
    
