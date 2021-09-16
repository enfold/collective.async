# -*- coding: utf-8 -*-

from ... import constants
from ...utils import get_tasks_for_user
from plone.app.layout.viewlets.common import ViewletBase


class AsyncViewlet(ViewletBase):

    tasks = list()

    def __init__(self, *args, **kwargs):
        self.tasks = get_tasks_for_user()
        return super(AsyncViewlet, self).__init__(*args, **kwargs)

    def get_ip_tasks(self):
        tasks = list()
        for task in self.tasks:
            if task.get('status') == constants.PROCESSING:
                tasks.append(task.get('task_id'))
        return tasks

    def get_error_tasks(self):
        tasks = list()
        for task in self.tasks:
            if task.get('status') == constants.ERROR:
                tasks.append(task.get('task_id'))
        return tasks
