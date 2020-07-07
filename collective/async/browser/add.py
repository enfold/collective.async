# -*- coding: utf-8 -*-
import json
import zope.component
from .. import constants
from .. import events
from .. import interfaces
from .. import tasks
from .. import utils
from AccessControl import Unauthorized
from plone.api import portal as portal_api
from plone.api import user as user_api
from Products.CMFPlone import PloneMessageFactory as _
from Products.statusmessages.interfaces import IStatusMessage
from plone.uuid.interfaces import IUUID
from plone.dexterity.browser import add
from plone.registry.interfaces import IRegistry
from zope.event import notify
from zope.publisher.browser import BrowserView


class AsyncAddForm(add.DefaultAddForm):
    success_message = _(u"Item will be created")

    def createAndAdd(self, data):
        obj = self.create(data)
        try:
            notify(events.AsyncBeforeAdd(self.context))
        except Unauthorized:
            IStatusMessage(self.request).add(
                _(u"You are not authorized to add content here.")
            )
            return
        except interfaces.AsyncValidationFailed, e:
            IStatusMessage(self.request).add(unicode(e))
            return

        uuid = IUUID(self.context, 0)
        obj_data = {
            "title": data.get("IDublinCore.title", data.get("title", u"")),
        }
        task_id = utils.register_task(
            obj=obj, obj_data=obj_data, action=constants.ADD, context=uuid
        )
        tasks.add_object.apply_async([self.context, task_id], {})
        utils.add_task_to_cookie(self.request, task_id)
        self.immediate_view = self.context.absolute_url()
        return obj


class AsyncAddView(add.DefaultAddView):
    form = AsyncAddForm
