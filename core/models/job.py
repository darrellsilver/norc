
from django.db.models import (Model,
    BooleanField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status
from norc.core.models.task import Task, BaseInstance, Instance
from norc.norc_utils.django_extras import queryset_exists

class Job(Task):
    """A Task composed of running several other Tasks."""
    
    def _get_start_nodes(self):
        start_nodes = []
        for n in self.nodes:
            if not queryset_exists(Dependency.objects.filter(child=n)):
                start_nodes.append(n)
        return start_nodes
    start_nodes = property(_get_start_nodes)
    
    def _run(self, instance):
        """Modified to give run() the instance object."""
        return self.run(instance)
    
    def run(self, instance):
        """Enqueue instances for all nodes that don't have dependencies."""
        for node in self.start_nodes:
            node_instance = SubInstance.objects.create(
                node=node,
                job_instance=instance,
                daemon=instance.daemon,
                schedule=instance.schedule)
            instance.schedule.queue.push(node_instance)
        # wait for all nodes to complete
    

class Node(Model):
    
    class Meta:
        app_label = 'core'
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    job = ForeignKey(Job, related_name='nodes')
    optional = BooleanField(default=False)
    
    def start(self, instance):
        self.task.start(instance)
        if self.optional or not Status.is_failure(instance.status):
            for node in self.sub_deps:
                # check for all deps
                ni, created = NodeInstance.objects.get_or_create(
                    source=node,
                    job_instance=instance.job_instance,
                )
                if created:
                    instance.job_instance.schedule.queue.push(ni)
        instance.job_instance.completion_check()
    
    def __unicode__(self):
        return u"Node in Job %s for Task %s" % (self.job, self.task)
    
    __repr__ = __unicode__
    

class NodeInstance(BaseInstance):
    """An instance of a node executed within a job."""
    
    # The node that spawned this instance.
    node = ForeignKey('Node')
    
    # The JobInstance that this NodeInstance belongs to.
    job_instance = ForeignKey(Instance, related_name='nodeinstances')
    
    def run(self):
        self.node.start()
    

class Dependency(Model):
    """One task Node's dependency on another.
    
    Represents an edge in the job's dependency digraph.
    
    """
    class Meta:
        app_label = 'core'
    
    parent = ForeignKey(Node, related_name='sub_deps')
    child = ForeignKey(Node, related_name='super_deps')
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        assert self.parent.job == self.child.job
    
    def __unicode__(self):
        return u"Dependency of %s on %s" % (self.child, self.parent)
    
    __repr__ = __unicode__
    
