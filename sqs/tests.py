
"""Unit tests for the norc.sqs module."""

from django.test import TestCase

from norc.sqs.models import SQSQueue
from norc.norc_utils import wait_until
from norc.norc_utils.testing import make_instance

class SQSQueueTest(TestCase):
    """Tests the ability to push and pop from an SQSQueue."""
    
    def setUp(self):
        self.queue = SQSQueue.objects.create(name='test')
        self.queue.queue.clear()
        self.item = make_instance()
        # wait_until(lambda: self.queue.queue.count() == 0)
    
    def test_push_pop(self):
        self.queue.push(self.item)
        self.i = None
        def get_item():
            self.i = self.queue.pop()
            return self.i != None
        wait_until(get_item)
        self.assertEqual(self.item, self.i)
    
    def test_invalid(self):
        self.assertRaises(AssertionError, lambda: self.queue.push(self.queue))
    
    def tearDown(self):
        pass
    
