# -*- coding: utf-8 -*-
import json
import zope.component
from .. import constants
from .. import tasks
from .. import utils
from AccessControl import Unauthorized
from plone.api import portal as portal_api
from plone.api import user as user_api
from plone.uuid.interfaces import IUUID
from plone.dexterity.browser import add
from plone.registry.interfaces import IRegistry
from zope.publisher.browser import BrowserView


class AsyncAddForm(add.DefaultAddForm):
    def createAndAdd(self, data):
        obj = self.create(data)
        uuid = IUUID(self.context, 0)
        task_id = utils.register_task(obj=obj, action=constants.ADD,
                                      context=uuid)
        tasks.add_object.apply_async([self.context, task_id], {})
        utils.add_task_to_cookie(self.request, task_id)
        self.immediate_view = self.context.absolute_url()
        return obj


class AsyncAddView(add.DefaultAddView):
    form = AsyncAddForm
