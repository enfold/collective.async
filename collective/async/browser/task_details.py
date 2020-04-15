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
        msg = ""
        action = task.get("action", None)
        context = task.get("context", None)
        if context:
            context = content_api.get(UID=context)
        else:
            context = self.context

        if action == constants.ADD:
            obj = task.get("obj")
            folder_url = ""
            if context:
                folder_url = context.absolute_url()
            msg = (
                "<span>Adding '<strong>{title}</strong>' to "
                "<a href='{url}'>{url}</a></span>"
            ).format(title=obj.title, url=folder_url)

        elif action == constants.EDIT:
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = (
                "<span>Saving changes to <a href='{url}'>{url}</a></span>"
            ).format(url=item_url)

        elif action == constants.DELETE:
            id = task.get("id", "")
            folder_url = ""
            if context:
                folder_url = context.absolute_url()
            msg = (
                "<span>Deleting item with id '<strong>{id}</strong>' "
                "from <a href='{url}'>{url}</a></span>"
            ).format(id=id, url=folder_url)

        elif action == constants.RENAME:
            id = task.get("id")
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = ("<span>Renaming item <a href='{url}'>{url}</a>.").format(
                url=item_url
            )
            old_title = task.get("old_title")
            new_title = task.get("new_title")
            if old_title != new_title:
                msg += " New title: <strong>%s</strong>." % new_title
            old_id = task.get("old_id")
            new_id = task.get("new_id")
            if old_id != new_id:
                msg += " New ID: <strong>%s</strong>." % new_id
            msg += "</span>"

        elif action == constants.PASTE:
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = (
                "<span>Pasting item in <a href='{url}'>{url}</a></span>"
            ).format(url=item_url)

        return msg

    def get_task_error(self, task):
        msg = ""
        action = task.get("action", None)
        context = task.get("context", None)
        err_msg = task.get("message", task.get("exc", ""))

        if context:
            context = content_api.get(UID=context)
        else:
            context = self.context

        if action == constants.ADD:
            obj = task.get("obj")
            folder_url = ""
            if context:
                folder_url = context.absolute_url()
            msg = (
                "<span>An error occurred when trying to add '"
                "<strong>{title}</strong>' to <a href='{url}'>{url}</a></span>"
            ).format(title=obj.title, url=folder_url)

        elif action == constants.EDIT:
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = (
                "<span>An error occurred when trying to save changes to "
                "<a href='{url}'>{url}</a></span>"
            ).format(url=item_url)

        elif action == constants.DELETE:
            id = task.get("id", "")
            folder_url = ""
            if context:
                folder_url = context.absolute_url()
            msg = (
                "<span>An error occurred when trying to delete item with id '"
                "<strong>{id}</strong>' from <a href='{url}'>{url}</a></span>"
            ).format(id=id, url=folder_url)

        elif action == constants.RENAME:
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = (
                "<span>An error occurred when trying to rename item "
                "<a href='{url}'>{url}</a>."
            ).format(url=item_url)
            old_title = task.get("old_title")
            new_title = task.get("new_title")
            if old_title != new_title:
                msg += " The new title was: <strong>%s</strong>." % new_title
            old_id = task.get("old_id")
            new_id = task.get("new_id")
            if old_id != new_id:
                msg += " The new ID was: <strong>%s</strong>." % new_id
            msg += "</span>"

        elif action == constants.PASTE:
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = (
                "<span>There was an error when pasting item in "
                "<a href='{url}'>{url}</a></span>"
            ).format(url=item_url)

        if err_msg:
            msg += (
                "<br/><br/><span>This is the error message:</span><br/><br/>"
                "<strong>%s</strong><br/>" % err_msg
            )

        return msg

    def get_task_success_message(self, task):
        msg = ""
        action = task.get("action", None)
        context = task.get("context", None)

        if context:
            context = content_api.get(UID=context)
        else:
            context = self.context

        if action == constants.ADD:
            obj_uid = task.get("obj_uid")
            obj_url = ""
            if obj_uid:
                obj = content_api.get(UID=obj_uid)
                obj_url = obj.absolute_url()

            msg = (
                "<p>Your new content has been created, you can visit it "
                "from here: <a href='{url}'>{url}</a></p>"
            ).format(url=obj_url)

        elif action == constants.EDIT:
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = (
                "<p>Changes to <a href='{url}'>{url}</a> have been saved.</p>"
            ).format(url=item_url)

        elif action == constants.DELETE:
            id = task.get("id", "")
            title = task.get("title", "")
            folder_url = ""
            if context:
                folder_url = context.absolute_url()
            msg = (
                "<span>Item with id '<strong>{id}</strong>' and title "
                "'<strong>{title}</strong>' has been deleted from "
                "<a href='{url}'>{url}</a></span>"
            ).format(id=id, title=title, url=folder_url)

        elif action == constants.RENAME:
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = (
                "<p>Item <a href='{url}'>{url}</a> has been successfully "
                "renamed.</p>"
            ).format(url=item_url)
            old_title = task.get("old_title")
            new_title = task.get("new_title")
            if old_title != new_title:
                msg += (
                    "<p>Old title: <strong>{old_title}</strong>. "
                    "New title: <strong>{new_title}</strong>.</p>"
                ).format(old_title=old_title, new_title=new_title)
            old_id = task.get("old_id")
            new_id = task.get("new_id")
            if old_id != new_id:
                msg += (
                    "<p>Old ID: <strong>{old_id}</strong>. "
                    "New ID: <strong>{new_id}</strong>.</p>"
                ).format(old_id=old_id, new_id=new_id)

        elif action == constants.PASTE:
            item_url = ""
            if context:
                item_url = context.absolute_url()
            msg = (
                "<p>Content was pasted at <a href='{url}'>{url}</a></p>"
            ).format(url=item_url)

        return msg
