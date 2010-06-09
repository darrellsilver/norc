
#
# Copyright (c) 2010, Perpetually.com, LLC.
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


"""Test schedule handling cases in the SchedulableTask class."""

import unittest
import random

from norc.core.models import SchedulableTask

class TestParseSchedule(unittest.TestCase):
    """Tests the SchedulableTask.parse_schedule_predefined method."""

    def setUp(self):
        """Initialize valid ranges for values."""
        self.valid_minutes = range(0, 60)
        self.valid_hours = range(0, 24)
        self.valid_days = range(1, 32)
        self.valid_months = range(1, 13)
        self.valid_weekdays = range(0, 7)

    def test_halfhourly_schedule(self):
        """Test the 'HALFHOURLY' schedule keyword."""
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('HALFHOURLY')
        # Half-hourly happens twice an hour.
        self.assertEquals(len(minutes), 2)
        for m in minutes:
            self.assertTrue(m in self.valid_minutes)
        # Test for half-hour difference.
        self.assertEquals(abs(minutes[1] - minutes[0]), 30)
        self.assertEquals(hours, self.valid_hours)          # Every hour.
        self.assertEquals(days, self.valid_days)            # Any day.
        self.assertEquals(months, self.valid_months)        # Any month.
        self.assertEquals(weekdays, self.valid_weekdays)    # Any weekday.
    
    def test_hourly_schedule(self):
        """Test the 'HOURLY' schedule keyword."""
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('HOURLY')
        if type(minutes) == list:
            print minutes
            self.assertEquals(len(minutes), 1)
            self.assertTrue(minutes[0] in self.valid_minutes)
        else:
            self.assertTrue(minutes in self.valid_minutes)
        self.assertEquals(hours, self.valid_hours)
        self.assertEquals(days, self.valid_days)
        self.assertEquals(months, self.valid_months)
        self.assertEquals(weekdays, self.valid_weekdays)
    
    def test_daily_schedule(self):
        """Test the 'DAILY' schedule keyword."""
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('DAILY')
        if type(minutes) == list:
            self.assertEquals(len(minutes), 1)
            self.assertTrue(minutes[0] in self.valid_minutes)
        else:
            self.assertTrue(minutes in self.valid_minutes)
        if type(hours) == list:
            self.assertEquals(len(hours), 1)
            self.assertTrue(hours[0] in self.valid_hours)
        else:
            self.assertTrue(hours in self.valid_hours)
        self.assertEquals(days, self.valid_days)
        self.assertEquals(months, self.valid_months)
        self.assertEquals(weekdays, self.valid_weekdays)

    def test_weekly_schedule(self):
        """Test the 'WEEKLY' schedule keyword."""
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('WEEKLY')
        if type(minutes) == list:
            self.assertEquals(len(minutes), 1)
            self.assertTrue(minutes[0] in self.valid_minutes)
        else:
            self.assertTrue(minutes in self.valid_minutes)
        if type(hours) == list:
            self.assertEquals(len(hours), 1)
            self.assertTrue(hours[0] in self.valid_hours)
        else:
            self.assertTrue(hours in self.valid_hours)
        self.assertEquals(days, self.valid_days)
        self.assertEquals(months, self.valid_months)
        if type(weekdays) == list:
            self.assertEquals(len(weekdays), 1)
            self.assertTrue(weekdays[0] in self.valid_weekdays)
        else:
            self.assertTrue(weekdays in self.valid_weekdays)

    def test_monthly_schedule(self):
        """Test the 'MONTHLY' schedule keyword."""
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('MONTHLY')
        if type(minutes) == list:
            self.assertEquals(len(minutes), 1)
        else:
            self.assertEquals(type(minutes), int)
        if type(hours) == list:
            self.assertEquals(len(hours), 1)
        else:
            self.assertEquals(type(hours), int)
        if type(days) == list:
            self.assertEquals(len(days), 1)
        else:
            self.assertEquals(type(days), int)
        self.assertEquals(months, self.valid_months)
        self.assertEquals(weekdays, self.valid_weekdays)

    def test_nonsense_schedule(self):
        """Test the handling of some nonsense input."""
        self.assertRaises(AssertionError,
                          SchedulableTask.parse_schedule_predefined,
                          'th1s1sM4dn3ss')
        self.assertRaises(AssertionError,
                          SchedulableTask.parse_schedule_predefined,
                          42)

if __name__ == '__main__':
    unittest.main()
