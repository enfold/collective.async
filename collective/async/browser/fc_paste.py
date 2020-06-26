# -*- coding: utf-8 -*-
import transaction
from AccessControl import Unauthorized
from .. import constants
from .. import events
from .. import interfaces
from .. import tasks
from .. import utils
from plone.app.content.browser.contents.paste import (
    PasteActionView as BasePasteActionView,
)
from Products.CMFPlone import PloneMessageFactory as _
from zope.i18n import translate
from plone.uuid.interfaces import IUUID
from zope.event import notify


class PasteActionView(BasePasteActionView):
    success_msg = _("Item to be pasted here")
    task_id = None

    def __call__(self):
        self.protect()
        self.errors = []

        parts = str(self.request.form["folder"].lstrip("/")).split("/")
        parent = self.site.unrestrictedTraverse("/".join(parts[:-1]))
        self.dest = parent.restrictedTraverse(parts[-1])

        try:
            uuid = IUUID(self.dest)
        except:
            # Site root does not have uuid
            uuid = 0

        sp = transaction.savepoint()
        try:
            notify(events.AsyncBeforePaste(self.dest))
        except Unauthorized:
            sp.rollback()
            self.errors.append(
                _(
                    u"You are not authorized to paste ${title} here.",
                    mapping={u"title": self.objectTitle(self.dest)},
                )
            )
            return self.message()
        except interfaces.AsyncValidationFailed, e:
            self.errors.append(unicode(e))
            return self.message()

        self.task_id = utils.register_task(action=constants.PASTE, context=uuid)

        tasks.paste.apply_async(
            [self.dest, self.request["__cp"], self.task_id], dict()
        )
        return self.message()

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
