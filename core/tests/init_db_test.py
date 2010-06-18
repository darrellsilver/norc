#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#

"""Tests the init_db script."""

from django.test import TestCase

from norc.utils import init_db
from norc.core.models import Job, Iteration, Resource, ResourceRegion

class TestParseSchedule(TestCase):
    """Tests the SchedulableTask.parse_schedule_predefined method."""

    def setUp(self):
        """Run the init_db script."""
        init_db.init_static()
        #pdb.set_trace()

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
    
    def test_iteration(self):
        """Tests that there is exactly one iteration."""
        self.assertEqual(len(Iteration.objects.all()), 1)
    
