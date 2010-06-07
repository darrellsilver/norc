

"""Test user preference module
"""

from django.test import TestCase 
from django.test.client import Client
from django.contrib.auth.models import User
from django.utils import simplejson

#from utils import init_db
#from utils import log
#log = log.Log()

#from unittest import TestCase

class UserPreferenceTest(TestCase):
    
    def setUp(self):
        #init_db.init_static()
        #self.user = User.objects.get(id=1)
        pass
    
    def test_simple(self, name, value):
        self.assertEquals(1,1)
