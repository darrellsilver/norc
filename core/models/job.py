
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
from norc.norc_utils.django_extras import queryset_exists

class Job(Task):
    """A Task composed of running several other Tasks."""
    
    def _get_start_nodes(self):
        start_nodes = []
        for n in self.nodes:
            if queryset_exists(Dependency.objects.filter(child=n)):
                start_nodes.append(n)
        return start_nodes
    start_nodes = property(_get_start_nodes)
    
    def run(self, iteration):
        """Enqueue iterations for all nodes that don't have dependencies."""
        for n in self.start_nodes:
            node_iter = NodeIteration(job_iter=iteration, source=n,
                daemon=iteration.daemon, schedule=iteration.schedule)
            node_iter.save()
            iteration.schedule.queue.push(node_iter)
    

class JobIteration(Iteration):
    
    class Meta(Iteration.Meta):
        proxy = True
    
    def completion_check(self):
        if self.source.nodes.count() == self.node_iters.filter(
                                            status=Status.SUCCESS).count():
            self.complete()
    
    def complete(self):
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
    """Node iterations need to be attached to their JobIteration."""
    
    job_iter = ForeignKey(JobIteration, related_name='node_iters')
    

class Dependency(Model):
    """One task Node's dependency on another.
    
    Represents an edge in the job's dependency digraph.
    
    """
    class Meta:
        app_label = 'core'
    
    parent = ForeignKey(Node, related_name='sub_deps')
    child = ForeignKey(Node, related_name='super_deps')
    
