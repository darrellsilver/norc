
"""Module for testing CommandTasks."""

import os
import time

from django.test import TestCase

from norc.core.models import CommandTask, Instance, Revision
from norc.core.constants import Status
from norc.norc_utils import log

class TestTask(TestCase):
    """Tests for Norc tasks."""
    
    def run_task(self, task):
        if isinstance(task, basestring):
            task = CommandTask.objects.create(name=task, command=task)
        return self.run_instance(Instance.objects.create(task=task)).status
    
    def run_instance(self, instance):
        instance.log = log.Log(os.devnull, echo=True)
        try:
            instance.start()
        except SystemExit:
            pass
        return Instance.objects.get(pk=instance.pk)
    
    def test_success(self):
        """Tests that a task can end with status SUCCESS."""
        self.assertEqual(Status.SUCCESS, self.run_task('echo "Success!"'))
    
    def test_failure(self):
        """Tests that a task can end with status FAILURE."""
        self.assertEqual(Status.FAILURE, self.run_task('exit 1'))
    
    def test_error(self):
        "Tests that a task can end with status ERROR."
        self.assertEqual(Status.ERROR, self.run_task('asd78sad7ftaoq'))
    
    def test_timedout(self):
        "Tests that a task can end with status TIMEDOUT."
        self.assertEqual(Status.TIMEDOUT, self.run_task(
            CommandTask.objects.create(
                name='Timeout', command='sleep 5', timeout=1)))
    
    def test_overflow(self):
        "Tests that a task can end with status OVERFLOW."
        import resource
        def boom():
            print "test"
            l = []
            class Foo(object):
                def __init__(self, bar):
                    self.bar = bar
            for i in range(1000000):
                l.append(Foo(i))
            def rec(n):
                print resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                if n == 0: return
                print n
                l=[]
                for i in range(1000):
                    l.append(Foo(i))
                return rec(n-1)
            rec(500)
        overflow = Instance.objects.create(task=CommandTask.objects.create(
            name='Overflow', command='echo "hi"'))
        overflow.run = boom
        # overflow.run(1)
        print resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        self.assertEqual(Status.OVERFLOW, self.run_instance(overflow).status)
    
    def test_nameless(self):
        "Tests that a task can be nameless."
        t = CommandTask.objects.create(command="echo 'Nameless!'")
        self.assertEqual(Status.SUCCESS, self.run_task(t))

    def test_revisions(self):
        r = Revision.objects.create(info="rev")
        t = CommandTask.objects.create(command="ls")
        i = Instance.objects.create(task=t)
        i.get_revision = lambda: r
        self.assertEqual(r, self.run_instance(i).revision)
