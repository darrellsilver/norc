
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
