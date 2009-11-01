
#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice, 
#       this list of conditions and the following disclaimer in the documentation 
#       and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
#     * 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#



##############################################
#
# Random django extensions that may prove generally useful.
#
#
#Darrell
#04/22/2009
##############################################


from django.db import models
from django.db import connection



class LockingManager(models.manager.Manager):
    """ Add lock/unlock functionality to manager.
    Darrell's notes:
        Darrell changed the class from which it inherits b/c it didn't match original.  
        See orig code for orig class.
        
        Changed 'manager' to 'objects' in example below; 
        seems to be a bug as indicated in comments at Source
	Source:
	    http://www.djangosnippets.org/snippets/833/
	Author:
	    miohtama
	Posted:
	    June 30, 2008
    Example::
        class Job(models.Model):
            objects = LockingManager()
            counter = models.IntegerField(null=True, default=0)
            @staticmethod
            def do_atomic_update(job_id)
                ''' Updates job integer, keeping it below 5 '''
                try:
                    # Ensure only one HTTP request can do this update at once.
                    Job.objects.lock()
                    
                    job = Job.object.get(id=job_id)
                    # If we don't lock the tables two simultanous
                    # requests might both increase the counter
                    # going over 5
                    if job.counter < 5:
                        job.counter += 1                                        
                        job.save()
                finally:
                    Job.objects.unlock()
    """
    
    def __init__(self, *args, **kwargs):
        models.manager.Manager.__init__(self, *args, **kwargs)
    
    def lock(self):
        """ Lock table. 
        
        Locks the object model table so that atomic update is possible.
        Simulatenous database access request pend until the lock is unlock()'ed.
        
        Note: If you need to lock multiple tables, you need to do lock them
        all in one SQL clause and this function is not enough. To avoid
        dead lock, all tables must be locked in the same order.
        
        See http://dev.mysql.com/doc/refman/5.0/en/lock-tables.html
        """
        cursor = connection.cursor()
        table = self.model._meta.db_table
        cursor.execute("LOCK TABLES %s WRITE" % table)
        row = cursor.fetchone()
        return row
    
    def unlock(self):
        """ Unlock the table. """
        cursor = connection.cursor()
        table = self.model._meta.db_table
        cursor.execute("UNLOCK TABLES")
        row = cursor.fetchone()
        return row

def agg_query_set_field(query_set, agg_by, field):
    # TODO use aggregation upon upgrade to django 1.1 
    #from django.db.models import Sum
    #bytes = ars.aggregate(Sum('bytes'))['bytes__avg']
    
    query_set = query_set.extra(select={'s':'%s(%s)' % (agg_by, field)
        , 'c':'count(1)'}).values('s', 'c')
    r = query_set[0]
    field_value = r['s']
    num = r['c']
    return (field_value, num)

#
