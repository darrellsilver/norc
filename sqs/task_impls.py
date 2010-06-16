
"""All implementations of SQSTask should be written or imported here."""

from norc.sqs.models import SQSTask

class SQSTaskTest(SQSTask):
    def __init__(self, *args, **kwargs):
        SQSTask.__init__(self, *args, **kwargs)
