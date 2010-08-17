
"""Test various utility functions/modules."""

from django.test import TestCase

from norc.core.models import Job, Instance, Resource, ResourceRegion
from norc.norc_utils import init_db
from norc.norc_utils.db import init_norc

class TestInitDB(TestCase):
    """Tests the init_db script."""

    def setUp(self):
        """Run the init_db script."""
        init_norc()

    def test_job(self):
        """Tests that there is exactly one job, 'DEMO_JOB'."""
        jobs = Job.objects.all()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].name, 'DEMO_JOB')
    
    def test_resource(self):    
        """Tests that there is exactly one resource, 'DATABASE_CONNECTION'."""
        resource = Resource.objects.all()
        self.assertEqual(len(resource), 1)
        self.assertEqual(resource[0].name, 'DATABASE_CONNECTION')
    
    def test_region(self):
        """Tests that there is exactly one resource region, 'DEMO_REGION'."""
        rr = ResourceRegion.objects.all()
        self.assertEqual(len(rr), 1)
        self.assertEqual(rr[0].name, 'DEMO_REGION')
    
    def test_instance(self):
        """Tests that there is exactly one instance."""
        self.assertEqual(len(Instance.objects.all()), 1)
    
