
from norc.core.models.task import Task, Iteration

def queryIsEmpty(q):
    try:
        q[0]
        return False
    except IndexError:
        return True

class Job(Task):
    
    class Meta:
        app_label = 'core'
    
    def _get_start_nodes(self):
        start_nodes = []
        for n in self.nodes:
            if queryIsEmpty(Dependency.objects.filter(child=n)):
                start_nodes.push(n)
        return start_nodes
    start_nodes = property(_get_start_nodes)
    
    def run(self, iteration):
        """Enqueue all nodes that don't have dependencies."""
        for n in self.start_nodes:
            iteration.schedule.queue.push()
    
class Node(Model):
    
    class Meta:
        app_label = 'core'
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey(task_type, task_id)
    job = ForeignKey(Job, related_name='nodes')
    
    def run(self):
        pass


class Dependency(Model):
    """One task Node's dependency on another.
    
    Represents an edge in the job's dependency digraph.
    
    """
    
    class Meta:
        app_label = 'core'
    
    parent = ForeignKey(Node, related_name='sub_deps')
    child = ForeignKey(Node, related_name='super_deps')
    
