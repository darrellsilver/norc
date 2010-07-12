
"""Module for testing anything related to daemons."""

import os, pdb, time
from django.test import TestCase

from django.conf import settings
from norc.core import report
from norc.core.models import *
from norc.utils import init_db, wait_until
from norc.core.tests.daemon_test import start_test_daemon

class TestTask(RunCommand):
    """A Task implementation for testing.
    
    Extending RunCommand because to function TestTask must utilize a
    previously defined model table.
    
    """
    class Meta:
        proxy = True    # Use the RunCommand database table.

class TestTasks(TestCase):
    """Tests for Norc tasks."""
    
    def setUp(self):
        """Initialize the DB and setup data."""
        init_db.init()
        self.daemon = start_test_daemon()
        self.job = Job.objects.all()[0]
        self.iter = Iteration.objects.all()[0]
        self.task = None
        self.get_nds = lambda: \
            report.nds(self.daemon.get_daemon_status().id)
        self.get_trs = lambda: \
            TaskRunStatus.objects.get(id=self.task.current_run_status.id)
    
    def test_task_success(self):
        """Tests that a task can run successfully."""
        class SuccessTask(TestTask):
            class Meta:
                proxy = True
            def run(self):
                self.ran = True
                return True
        self.task = SuccessTask(job=self.job, timeout=60)
        self.task.save()
        self.task.do_run(self.iter, self.get_nds())
        self.assertTrue(self.task.ran)
        self.assertEqual(self.get_trs().status, TaskRunStatus.STATUS_SUCCESS)
    
    def test_task_error(self):
        """Tests that a task can run successfully."""
        class ErrorTask(TestTask):
            class Meta:
                proxy = True
            def run(self):
                raise Exception()
        self.task = ErrorTask(job=self.job, timeout=60)
        self.task.save()
        self.task.do_run(self.iter, self.get_nds())
        self.assertEqual(self.get_trs().status, TaskRunStatus.STATUS_ERROR)
    
    def test_task_timeout(self):
        class TimeOutTask(TestTask):
            class Meta:
                proxy = True
            def run(self):
                time.sleep(20)
                return True
        self.task = TimeOutTask(job=self.job, timeout=1)
        self.task.save()
        self.task.do_run(self.iter, self.get_nds())
        self.assertEqual(self.get_trs().status, TaskRunStatus.STATUS_TIMEDOUT)
    
    def tearDown(self):
        self.daemon.request_stop()
        wait_until(lambda: self.get_nds().is_done(), 3)
    