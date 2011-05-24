
from django.test import TestCase

from norc.core.models import DBQueue, QueueGroup, QueueGroupItem, Instance
from norc.norc_utils import wait_until
from norc.norc_utils.testing import *

class DBQueueTest(TestCase):
    """Super simple test that pushes and pops something from the queue."""
    
    def setUp(self):
        self.queue = DBQueue.objects.create(name='test')
        self.item = make_instance()
    
    def test_push_pop(self):
        self.queue.push(self.item)
        self.assertEqual(self.queue.peek(), self.item)
        self.assertEqual(self.queue.pop(), self.item)
    
    def test_invalid(self):
        self.assertRaises(AssertionError, lambda: self.queue.push(self.queue))
    
    def tearDown(self):
        pass
    

class QueueGroupTest(TestCase):
    """Tests and demonstrates the usage of QueueGroups."""
    
    def setUp(self):
        self.group = g = QueueGroup.objects.create(name='TestGroup')
        self.q1 = DBQueue.objects.create(name="Q1")
        self.q2 = DBQueue.objects.create(name="Q2")
        self.q3 = DBQueue.objects.create(name="Q3")
        QueueGroupItem.objects.create(group=g, queue=self.q1, priority=1)
        QueueGroupItem.objects.create(group=g, queue=self.q2, priority=2)
        QueueGroupItem.objects.create(group=g, queue=self.q3, priority=3)
        self.task = make_task()
    
    def new_instance(self):
        return Instance.objects.create(task=self.task)
    
    def test_push_pop(self):
        """Test that all three queues work."""
        item = self.new_instance()
        self.q1.push(item)
        self.assertEqual(self.group.pop(), item)
        self.q2.push(item)
        self.assertEqual(self.group.pop(), item)
        self.q3.push(item)
        self.assertEqual(self.group.pop(), item)
    
    def test_priority(self):
        """Test that things get popped in priority order."""
        p1 = [self.new_instance() for _ in range(10)]
        p2 = [self.new_instance() for _ in range(10)]
        p3 = [self.new_instance() for _ in range(10)]
        for i in p3: self.q3.push(i)
        for i in p2: self.q2.push(i)
        for i in p1: self.q1.push(i)
        popped = [self.group.pop() for _ in range(30)]
        self.assertEqual(popped, p1 + p2 + p3)
    
    def test_no_push(self):
        """Test that pushing to a QueueGroup fails."""
        self.assertRaises(NotImplementedError, lambda: self.group.push(None))
    
    def tearDown(self):
        pass
    
