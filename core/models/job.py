
from django.db.models import (Model,
    CharField,
    DateTimeField,
    IntegerField,
    PositiveIntegerField,
    SmallPositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status
from norc.core.models.task import Task, Iteration

def queryset_exists(q):
    try:
        q[0]
        return True
    except IndexError:
        return False

class Job(Task):
    
    def _get_start_nodes(self):
        start_nodes = []
        for n in self.nodes:
            if queryset_exists(Dependency.objects.filter(child=n)):
                start_nodes.push(n)
        return start_nodes
    start_nodes = property(_get_start_nodes)
    
    def run(self, iteration):
        """Enqueue all nodes that don't have dependencies."""
        for n in self.start_nodes:
            node_iter = NodeIteration(job_iter=iteration, spawner=n,
                daemon=iteration.daemon, schedule=iteration.schedule)
            iteration.schedule.queue.push(node_iter)
    

class JobIteration(Iteration):
    
    def finished_check(self):
        pass
    
    def finished(self):
        """Called when all of this Job's TaskNodes have run."""
        pass

class TaskNode(Model):
    
    class Meta:
        app_label = 'core'
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey(task_type, task_id)
    job = ForeignKey(Job, related_name='nodes')
    
    def run(self):
        
        # Run task, then check dependents.
        pass
    

class NodeIteration(Iteration):
    
    job_iter = ForeignKey(Iteration, related_name='nodes')
    
    def start(self):
        Iteration.start(self)
        

class Dependency(Model):
    """One task Node's dependency on another.
    
    Represents an edge in the job's dependency digraph.
    
    """
    
    class Meta:
        app_label = 'core'
    
    parent = ForeignKey(Node, related_name='sub_deps')
    child = ForeignKey(Node, related_name='super_deps')
    
