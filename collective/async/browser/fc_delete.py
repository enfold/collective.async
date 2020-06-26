# -*- coding: utf-8 -*-
import transaction
from .. import constants
from .. import events
from .. import interfaces
from .. import tasks
from .. import utils
from AccessControl import Unauthorized
from plone.app.content.browser.contents.delete import (
    DeleteActionView as BaseDeleteActionView,
)
from plone.uuid.interfaces import IUUID
from Products.CMFPlone import PloneMessageFactory as _
from zope.event import notify
from zope.i18n import translate


class DeleteActionView(BaseDeleteActionView):
    task_id = None
    success_msg = _("Item being processed for deletion")

    def action(self, obj):
        parent = obj.aq_inner.aq_parent
        title = self.objectTitle(obj)

        try:
            lock_info = obj.restrictedTraverse("@@plone_lock_info")
        except AttributeError:
            lock_info = None

        if lock_info is not None and lock_info.is_locked():
            self.errors.append(
                _(
                    u"${title} is locked and cannot be deleted.",
                    mapping={u"title": title},
                )
            )
            return
        else:
            el_id = obj.getId()
            try:
                uuid = IUUID(parent)
            except:
                # Site root does not have uuid
                uuid = 0

            sp = transaction.savepoint()
            try:
                notify(events.AsyncBeforeDelete(obj))
            except Unauthorized:
                sp.rollback()
                self.errors.append(
                    _(
                        u"You are not authorized to delete ${title}.",
                        mapping={u"title": title},
                    )
                )
                return
            except interfaces.AsyncValidationFailed, e:
                self.errors.append(unicode(e))
                return

            self.task_id = utils.register_task(
                action=constants.DELETE, context=uuid, id=el_id
            )
            tasks.delete.apply_async(
                [parent, obj.getId(), title, self.task_id], dict()
            )

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
        if self.task_id:
            results["task_id"] = self.task_id

        return self.json(results)
