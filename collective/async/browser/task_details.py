# -*- coding: utf-8 -*-
from .. import constants
from .. import utils
from AccessControl import Unauthorized
from plone.api import user as user_api
from plone.api import content as content_api
from zope.publisher.browser import BrowserView


class TaskDetails(BrowserView):
    in_progress_tasks = False
    task_id = None

    def __call__(self, *args, **kwargs):
        if user_api.is_anonymous():
            raise Unauthorized
        request = self.request
        self.task_id = request.get("task_id")
        if not self.task_id:
            self.in_progress_tasks = True
        return self.index()

    def get_tasks_from_cookie(self):
        tasks = utils.get_tasks_from_cookie(self.request)
        return tasks

    def get_task(self, task_id=None):
        if not task_id:
            task_id = self.task_id
        result = dict()
        if utils.has_task(task_id):
            task = utils.get_task(task_id)
            result = dict(task)
        return result

    def get_task_description(self, task):
        return utils.get_task_description(task)

    def get_task_error(self, task):

        msg = utils.get_task_error_message(task)
        err_msg = task.get("message", task.get("exc", ""))

        if err_msg:
            msg += (
                "<br/><br/><span>This is the error message:</span><br/><br/>"
                "<strong>%s</strong><br/>" % err_msg
            )

        return msg

    def get_task_success_message(self, task):
        return utils.get_task_success_message(task)
