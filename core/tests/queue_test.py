
from django.test import TestCase

from norc.core.models import DBQueue
from norc.norc_utils import wait_until
from norc.norc_utils.testing import make_instance

class DBQueueTest(TestCase):
    """Super simple test that pushes and pops something from the queue."""
    
    def setUp(self):
        self.queue = DBQueue.objects.create(name='test')
        self.item = make_instance()
    
    def test_push_pop(self):
        self.queue.push(self.item)
        wait_until(self.queue.peek, 10)
        i = self.queue.pop()
        self.assertEqual(self.item, i)
    
    def test_invalid(self):
        self.assertRaises(AssertionError, lambda: self.queue.push(self.queue))
    
    def tearDown(self):
        pass
    
