
"""Module for testing CommandTasks."""

import os, sys
import time

from django.test import TestCase

from norc.core.models import CommandTask, Instance, Revision
from norc.core.constants import Status
from norc.norc_utils import log

class TestTask(TestCase):
    """Tests for Norc tasks."""
    
    def run_task(self, task):
        if type(task) == str:
            task = CommandTask.objects.create(name=task, command=task)
        return self.run_instance(Instance.objects.create(task=task)).status
    
    def run_instance(self, instance):
        instance.log = log.Log(os.devnull)
        try:
            instance.start()
        except SystemExit:
            pass
        return Instance.objects.get(pk=instance.pk)
    
    def disarm(self, instance):
        """Have to soften _nuke sometimes or the test process will die."""
        def _nuke():
            sys.exit(1)
        instance._nuke = _nuke
    
    def test_success(self):
        """Tests that a task can end with status SUCCESS."""
        self.assertEqual(Status.SUCCESS, self.run_task('echo "Success!"'))
    
    def test_failure(self):
        """Tests that a task can end with status FAILURE."""
        self.assertEqual(Status.FAILURE, self.run_task('exit 1'))
        self.assertEqual(Status.FAILURE, self.run_task('asd78sad7ftaoq'))
    
    def test_timeout(self):
        "Tests that a task can end with status TIMEDOUT."
        task = CommandTask.objects.create(
            name='Timeout', command='sleep 5', timeout=1)
        instance = Instance.objects.create(task=task)
        self.disarm(instance)
        self.assertEqual(Status.TIMEDOUT, self.run_instance(instance).status)
    
    def test_final(self):
        task = CommandTask.objects.create(name='Nothing', command='sleep 0')
        instance = Instance.objects.create(task=task)
        self.disarm(instance)
        def final():
            instance.status = Status.ERROR
        instance.final = final
        self.assertEqual(Status.ERROR, self.run_instance(instance).status)
    
    def test_final_timeout(self):
        t = CommandTask.objects.create(name='Nothing', command='sleep 0')
        instance = Instance.objects.create(task=t)
        self.disarm(instance)
        from norc.core.models import task
        task.FINALLY_TIMEOUT = 1
        def final():
            import time
            time.sleep(2)
        instance.final = final
        self.assertEqual(Status.TIMEDOUT, self.run_instance(instance).status)
    
    def test_double_timeout(self):
        """Tests a task timing out and then its final block timing out.
        
        NOTE: because the "nuking" of the process can't occur in a test
        environment, this test actually results in the final clause being
        run twice.  This won't happen in a real setting because _nuke()
        is aptly named.
        
        """
        t = CommandTask.objects.create(
            name='Nothing', command='sleep 2', timeout=1)
        instance = Instance.objects.create(task=t)
        self.disarm(instance)
        from norc.core.models import task
        task.FINALLY_TIMEOUT = 1
        def final():
            import time
            time.sleep(2)
        instance.final = final
        self.assertEqual(Status.TIMEDOUT, self.run_instance(instance).status)
    
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
