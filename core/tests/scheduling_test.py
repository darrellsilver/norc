
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
        self.assertEqual(len(minutes), 2)
        for m in minutes:
            self.assertTrue(m in self.valid_minutes)
        # Test for half-hour difference.
        self.assertEqual(abs(minutes[1] - minutes[0]), 30)
        self.assertEqual(hours, self.valid_hours)          # Every hour.
        self.assertEqual(days, self.valid_days)            # Any day.
        self.assertEqual(months, self.valid_months)        # Any month.
        self.assertEqual(weekdays, self.valid_weekdays)    # Any weekday.
    
    def test_hourly_schedule(self):
        """Test the 'HOURLY' schedule keyword."""
        
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('HOURLY')
        if type(minutes) == list:
            print minutes
            self.assertEqual(len(minutes), 1)
            self.assertTrue(minutes[0] in self.valid_minutes)
        else:
            self.assertTrue(minutes in self.valid_minutes)
        self.assertEqual(hours, self.valid_hours)
        self.assertEqual(days, self.valid_days)
        self.assertEqual(months, self.valid_months)
        self.assertEqual(weekdays, self.valid_weekdays)
    
    def test_daily_schedule(self):
        """Test the 'DAILY' schedule keyword."""
        
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('DAILY')
        if type(minutes) == list:
            self.assertEqual(len(minutes), 1)
            self.assertTrue(minutes[0] in self.valid_minutes)
        else:
            self.assertTrue(minutes in self.valid_minutes)
        if type(hours) == list:
            self.assertEqual(len(hours), 1)
            self.assertTrue(hours[0] in self.valid_hours)
        else:
            self.assertTrue(hours in self.valid_hours)
        self.assertEqual(days, self.valid_days)
        self.assertEqual(months, self.valid_months)
        self.assertEqual(weekdays, self.valid_weekdays)
    
    def test_weekly_schedule(self):
        """Test the 'WEEKLY' schedule keyword."""
        
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('WEEKLY')
        if type(minutes) == list:
            self.assertEqual(len(minutes), 1)
            self.assertTrue(minutes[0] in self.valid_minutes)
        else:
            self.assertTrue(minutes in self.valid_minutes)
        if type(hours) == list:
            self.assertEqual(len(hours), 1)
            self.assertTrue(hours[0] in self.valid_hours)
        else:
            self.assertTrue(hours in self.valid_hours)
        self.assertEqual(days, self.valid_days)
        self.assertEqual(months, self.valid_months)
        if type(weekdays) == list:
            self.assertEqual(len(weekdays), 1)
            self.assertTrue(weekdays[0] in self.valid_weekdays)
        else:
            self.assertTrue(weekdays in self.valid_weekdays)
    
    def test_monthly_schedule(self):
        """Test the 'MONTHLY' schedule keyword."""
        
        minutes, hours, days, months, weekdays = \
            SchedulableTask.parse_schedule_predefined('MONTHLY')
        if type(minutes) == list:
            self.assertEqual(len(minutes), 1)
        else:
            self.assertEqual(type(minutes), int)
        if type(hours) == list:
            self.assertEqual(len(hours), 1)
        else:
            self.assertEqual(type(hours), int)
        if type(days) == list:
            self.assertEqual(len(days), 1)
        else:
            self.assertEqual(type(days), int)
        self.assertEqual(months, self.valid_months)
        self.assertEqual(weekdays, self.valid_weekdays)
    
    def test_nonsense_input(self):
        """Test the handling of some nonsense input."""
        
        self.assertRaises(AssertionError,
                          SchedulableTask.parse_schedule_predefined,
                          'th1s1sM4dn3ss')
        self.assertRaises(AssertionError,
                          SchedulableTask.parse_schedule_predefined,
                          42)
    

#if __name__ == '__main__':
#    unittest.main()
