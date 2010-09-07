
"""Module for testing anything related to daemons."""

import os
import time

from django.test import TestCase

from norc.core.models import CommandTask, Instance
from norc.core.constants import Status
from norc.norc_utils import log

class TestCommandTask(TestCase):
    """Tests for Norc tasks."""
    
    def run_task(self, ct):
        if type(ct) == str:
            ct = CommandTask.objects.create(name=ct, command=ct)
        instance = Instance.objects.create(task=ct)
        # instance.log = log.Log(os.devnull)
        instance.start()
        return Instance.objects.get(pk=instance.pk).status
    
    def test_status(self):
        """Tests that a task can run successfully."""
        self.assertEqual(Status.SUCCESS, self.run_task('echo "Success!"'))
        self.assertEqual(Status.FAILURE, self.run_task('exit 1'))
        self.assertEqual(Status.ERROR, self.run_task('asd78sad7ftao;q'))
        self.assertEqual(Status.TIMEDOUT, self.run_task(
            CommandTask.objects.create(
                name='Timeout', command='sleep 5', timeout=1)))
    
