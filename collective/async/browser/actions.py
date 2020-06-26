# -*- coding: utf-8 -*-
import json
from .. import constants
from .. import events
from .. import interfaces
from .. import tasks
from .. import utils
from AccessControl import getSecurityManager
from AccessControl import Unauthorized
from Acquisition import aq_inner
from Acquisition import aq_parent
from plone.api import content as content_api
from plone.api import user as user_api
from plone.app.content.browser import actions as plone_actions
from plone.uuid.interfaces import IUUID
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone import utils as plone_utils
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import button
from zope.event import notify
from zope.publisher.browser import BrowserView


class DeleteConfirmationForm(plone_actions.DeleteConfirmationForm):
    @button.buttonAndHandler(_(u"Delete"), name="Delete")
    def handle_delete(self, action):
        context = self.context
        request = self.request
        inner = aq_inner(context)
        parent = aq_parent(inner)
        title = plone_utils.safe_unicode(context.Title())
        if context.aq_chain == inner.aq_chain:
            el_id = context.getId()
            uuid = IUUID(parent, 0)

            try:
                notify(events.AsyncBeforeDelete(context))
            except Unauthorized:
                IStatusMessage(request).add(
                    _(
                        u"You are not authorized to delete ${title}.",
                        mapping={u"title": title},
                    )
                )
                return request.response.redirect(context.absolute_url())
            except interfaces.AsyncValidationFailed, e:
                IStatusMessage(request).add(unicode(e))
                return request.response.redirect(context.absolute_url())

            task_id = utils.register_task(
                action=constants.DELETE, context=uuid, id=el_id
            )
            tasks.delete.apply_async(
                [parent, context.getId(), title, task_id], dict()
            )

            utils.add_task_to_cookie(request, task_id)
            return request.response.redirect(parent.absolute_url())
        else:
            IStatusMessage(request).add(
                _(
                    u'"${title}" has already been deleted',
                    mapping={u"title": title},
                )
            )
            return request.response.redirect(parent.absolute_url())


class RenameForm(plone_actions.RenameForm):
    @button.buttonAndHandler(_(u"Rename"), name="Rename")
    def handle_rename(self, action):
        request = self.request
        data, errors = self.extractData()
        if errors:
            return
        context = self.context
        parent = aq_parent(aq_inner(context))
        sm = getSecurityManager()
        if not sm.checkPermission("Copy or Move", parent):
            raise Unauthorized(
                _(
                    u"Permission denied to rename ${title}.",
                    mapping={u"title": context.title},
                )
            )

        newid = data["new_id"]
        newtitle = data["new_title"]

        try:
            notify(events.AsyncBeforeRename(context, newid, newtitle))
        except Unauthorized:
            IStatusMessage(self.request).add(
                _(
                    u"Permission denied to rename ${title}.",
                    mapping={u"title": context.title},
                )
            )
            return self.request.response.redirect(context.absolute_url())
        except interfaces.AsyncValidationFailed, e:
            IStatusMessage(request).add(unicode(e))
            return request.response.redirect(context.absolute_url())

        uuid = IUUID(context, 0)
        task_id = utils.register_task(
            action=constants.RENAME,
            context=uuid,
            old_title=context.title,
            old_id=context.id,
            new_id=newid,
            new_title=newtitle,
        )
        tasks.rename.apply_async(
            [context, data["new_id"], data["new_title"], task_id], dict()
        )
        utils.add_task_to_cookie(self.request, task_id)
        return self.request.response.redirect(parent.absolute_url())


class ObjectPasteView(plone_actions.ObjectPasteView):
    def do_action(self):
        context = self.context
        request = self.request
        if not context.cb_dataValid():
            return self.do_redirect(
                self.canonical_object_url,
                _(u"Copy or cut one or more items to paste."),
                "error",
            )

        try:
            notify(events.AsyncBeforePaste(context))
        except Unauthorized:
            IStatusMessage(request).add(
                _(u"Permission denied to paste content in here")
            )
            return request.response.redirect(context.absolute_url())
        except interfaces.AsyncValidationFailed, e:
            IStatusMessage(request).add(unicode(e))
            return request.response.redirect(context.absolute_url())

        uuid = IUUID(context, 0)
        task_id = utils.register_task(action=constants.PASTE, context=uuid)

        tasks.paste.apply_async([context, request["__cp"], task_id], dict())

        utils.add_task_to_cookie(request, task_id)
        return request.response.redirect(context.absolute_url())


class CheckForTasks(BrowserView):
    def should_reload(self, task):
        result = False
        current_location = self.request.get("current_location", None)
        if current_location:
            try:
                current_location = json.loads(current_location)
            except Exception:
                current_location = dict()

        url = ""
        if current_location:
            if "origin" in current_location and "pathname" in current_location:
                url = current_location["origin"] + current_location["pathname"]
            elif "href" in current_location:
                url = current_location["href"]
            else:
                url = ""

        if url:
            # First some conditions when view should never be reloaded
            if "++add++" not in url and not url.endswith("edit"):
                if url.endswith("@@task-details"):
                    qs = current_location["search"]
                    if "task_id" in qs and task.get("task_id") in qs:
                        result = True
                    elif "task_id" not in qs:
                        result = True
                else:
                    action = task.get("action", None)
                    context = task.get("context", None)
                    if context:
                        context = content_api.get(UID=context)
                    if not context:
                        context = self.context
                    if (
                        action == constants.ADD
                        and context.absolute_url() == url
                    ):
                        result = True
                    elif action == constants.RENAME:
                        if (
                            context.absolute_url() == url
                            or context.aq_parent.absolute_url() == url
                        ):
                            # We are currently at the folder holding the
                            # renamed object.
                            result = True
                        else:
                            old_id = task.get("old_id", "")
                            old_url = "%s/%s" % (
                                context.aq_parent.absolute_url(), old_id
                            )
                            if url == old_url:
                                # We are currently at the old object
                                # that was renamed.
                                result = True
                    elif (
                        action == constants.DELETE
                        and context.absolute_url() == url
                    ):
                        result = True
                    elif (
                        action == constants.PASTE
                        and context.absolute_url() == url
                    ):
                        result = True
                    elif action == constants.EDIT:
                        if context.absolute_url() == url:
                            result = True
                        elif context.aq_parent.absolute_url() == url:
                            # Only redirect if the edit was done for the title
                            for iface, fields in task.get("changes"):
                                if (
                                    iface
                                    == "plone.app.dexterity.behaviors.metadata.IBasic"
                                    and "IDublinCore.title" in fields
                                ):
                                    result = True

        return result

    def __call__(self, *args, **kwargs):
        if user_api.is_anonymous():
            raise Unauthorized
        request = self.request
        task_ids = request.get("task_ids")
        result = {
            "processing": list(),
            "error": list(),
            "success": list(),
            "should_reload": False,
        }
        if task_ids:
            try:
                task_ids = json.loads(task_ids)
            except Exception:
                task_ids = list()

        for task_id in task_ids:
            if utils.has_task(task_id):
                task = dict(utils.get_task(task_id))
                action = task.get("action", None)
                if action == constants.ADD and "obj" in task:
                    del task["obj"]
                if task["status"] == constants.PROCESSING:
                    result["processing"].append(task)
                elif task["status"] == constants.SUCCESS:
                    result["success"].append(task)
                    if not result["should_reload"]:
                        result["should_reload"] = self.should_reload(task)
                elif task["status"] == constants.ERROR:
                    err_task = {"task_id": task.get("task_id", "")}
                    err_msg = ""
                    if action == constants.ADD:
                        err_msg = (
                            "An error occurred when trying to add an item."
                        )
                    elif action == constants.EDIT:
                        err_msg = (
                            "An error occurred when trying to save changes "
                            "to an item."
                        )
                    elif action == constants.DELETE:
                        err_msg = (
                            "An error occurred when trying to delete an item."
                        )
                    elif action == constants.RENAME:
                        err_msg = (
                            "An error occurred when trying to rename an item."
                        )
                    elif action == constants.PASTE:
                        err_msg = (
                            "An error occurred when trying to paste an item."
                        )

                    err_task["error_message"] = err_msg
                    result["error"].append(err_task)

        request.response.setHeader(
            "Content-Type", "application/json; charset=utf-8"
        )
        return json.dumps(result)
