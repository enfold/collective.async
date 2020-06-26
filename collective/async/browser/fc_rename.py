# -*- coding: utf-8 -*-
import six
import transaction
from AccessControl import Unauthorized
from Acquisition import aq_inner
from .. import constants
from .. import events
from .. import interfaces
from .. import tasks
from .. import utils
from plone.app.content.browser.contents.rename import (
    RenameActionView as BaseRenameActionView,
)
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFCore.utils import getToolByName
from plone.uuid.interfaces import IUUID
from zope.event import notify
from zope.i18n import translate


class RenameActionView(BaseRenameActionView):
    success_msg = _("Items going to be renamed")
    failure_msg = _("Failed to rename items")
    task_ids = list()

    def __call__(self):
        self.errors = []
        self.protect()
        context = aq_inner(self.context)

        catalog = getToolByName(context, "portal_catalog")
        mtool = getToolByName(context, "portal_membership")

        missing = []
        for key in self.request.form.keys():
            if not key.startswith("UID_"):
                continue
            index = key.split("_")[-1]
            uid = self.request.form[key]
            brains = catalog(UID=uid, show_inactive=True)
            if len(brains) == 0:
                missing.append(uid)
                continue
            obj = brains[0].getObject()
            title = self.objectTitle(obj)
            if not mtool.checkPermission("Copy or Move", obj):
                self.errors(
                    _(
                        u"Permission denied to rename ${title}.",
                        mapping={u"title": title},
                    )
                )
                continue

            obid = obj.getId()
            title = obj.Title()
            newid = self.request.form["newid_" + index]
            if six.PY2:
                newid = newid.encode("utf8")
            newtitle = self.request.form["newtitle_" + index]

            sp = transaction.savepoint(optimistic=True)
            try:
                notify(events.AsyncBeforeRename(obj, newid, newtitle))
            except Unauthorized:
                sp.rollback()
                self.errors.append(
                    _(u"Error renaming ${title}", mapping={"title": title})
                )
                continue
            except interfaces.AsyncValidationFailed, e:
                sp.rollback()
                self.errors.append(unicode(e))
                continue

            uuid = IUUID(obj, 0)
            task_id = utils.register_task(
                action=constants.RENAME,
                context=uuid,
                old_title=title,
                old_id=obid,
                new_id=newid,
                new_title=newtitle,
            )
            tasks.rename.apply_async(
                [obj, newid, newtitle, task_id], dict()
            )
            self.task_ids.append(task_id)

        return self.message(missing)

    def message(self, missing=[]):
        if len(missing) > 0:
            self.errors.append(
                _(
                    "${items} could not be found",
                    mapping={"items": str(len(missing))},
                )
            )
        if self.errors:
            msg = self.failure_msg
        else:
            msg = self.success_msg

        translated_msg = translate(msg, context=self.request)
        if self.errors:
            translated_errors = [
                translate(error, context=self.request) for error in self.errors
            ]
            translated_msg = u"{0:s}: {1:s}".format(
                translated_msg, u"\n".join(translated_errors)
            )

        results = {
            "status": "warning" if self.errors else "success",
            "msg": translated_msg,
        }
        if self.task_ids:
            results["task_ids"] = self.task_ids

        return self.json(results)
