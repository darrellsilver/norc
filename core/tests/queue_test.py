
from django.test import TestCase

from norc.core.models import DBQueue
from norc.norc_utils import wait_until

class DBQueueTest(TestCase):
    """Super simple test that pushes and pops something from the queue."""
    
    def setUp(self):
        self.queue = DBQueue.objects.create(name='test')
    
    def test_push_pop(self):
        self.queue.push(self.queue)
        wait_until(self.queue.peek, 10)
        q = self.queue.pop()
        self.assertEqual(self.queue, q)
    
    def tearDown(self):
        pass
    
