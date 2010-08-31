
""""""

import unittest
import re
from threading import Thread

from django.test import TestCase

from norc.core.models import Job, Node, Dependency, Instance, Schedule
from norc.norc_utils import wait_until, log, testing

class JobTest(TestCase):
    
    def queue_items(self):
        items = []
        while self.queue.count() > 0:
            items.append(self.queue.pop())
        return items
    
    def setUp(self):
        self.queue = testing.make_queue()
        self.tasks = [testing.make_task('JobTask%s' % i) for i in range(6)]
        self.job = Job.objects.create(name='TestJob')
        self.nodes = [Node.objects.create(task=self.tasks[i], job=self.job)
            for i in range(6)]
        n = self.nodes
        Dependency.objects.create(parent=n[0], child=n[2])
        Dependency.objects.create(parent=n[0], child=n[3])
        Dependency.objects.create(parent=n[1], child=n[4])
        Dependency.objects.create(parent=n[2], child=n[3])
        Dependency.objects.create(parent=n[2], child=n[5])
        Dependency.objects.create(parent=n[3], child=n[5])
        Dependency.objects.create(parent=n[4], child=n[5])
    
    def test_job(self):
        schedule = Schedule.create(self.job, self.queue, 1)
        instance = Instance.objects.create(task=self.job, schedule=schedule)
        instance.log = log.Log(debug=True)
        self.thread = Thread(target=instance.start)
        self.thread.start()
        wait_until(lambda: self.queue.count() == 2, 2)
        self.assertEqual(set([i.item.node for i in self.queue.items.all()]),
            set([self.nodes[0], self.nodes[1]]))
        for i in self.queue_items():
            i.start()
        self.assertEqual(set([i.item.node for i in self.queue.items.all()]),
            set([self.nodes[2], self.nodes[4]]))
        for i in self.queue_items():
            i.start()
        self.assertEqual(set([i.item.node for i in self.queue.items.all()]),
            set([self.nodes[3]]))
        for i in self.queue_items():
            i.start()
        self.assertEqual(set([i.item.node for i in self.queue.items.all()]),
            set([self.nodes[5]]))
        for i in self.queue_items():
            i.start()
        self.thread.join(2)
        self.assertFalse(self.thread.isAlive())
    
