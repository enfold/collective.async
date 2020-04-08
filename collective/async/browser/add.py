# -*- coding: utf-8 -*-
import json
import zope.component
from .. import constants
from .. import tasks
from .. import utils
from AccessControl import Unauthorized
from plone.api import portal as portal_api
from plone.api import user as user_api
from plone.dexterity.browser import add
from plone.registry.interfaces import IRegistry
from zope.publisher.browser import BrowserView


class AsyncAddForm(add.DefaultAddForm):

    def createAndAdd(self, data):
        obj = self.create(data)
        task_id = utils.register_task(obj=obj)
        tasks.add_object.apply_async([self.context, task_id], {})
        url = self.context.absolute_url() + \
            '/wait-for-new-object?task_id=%s' % task_id
        self.immediate_view = url
        return obj


class AsyncAddView(add.DefaultAddView):
    form = AsyncAddForm


class CheckForNewObject(BrowserView):

    def __call__(self, *args, **kwargs):
        if user_api.is_anonymous():
            raise Unauthorized
        request = self.request
        task_id = request.get('task_id')
        result = dict()
        error_message = u'Sorry, there was an error creating your object.'
        if utils.has_task(task_id):
            task = utils.get_task(task_id)
            result['status'] = status = task['status']
            if status == constants.SUCCESS:
                catalog = portal_api.get_tool('portal_catalog')
                registry = zope.component.getUtility(IRegistry)
                use_view_action = registry.get(
                    'plone.types_use_view_action_in_listings', [])
                brains = catalog.searchResults(UID=task['obj_uid'])
                if len(brains) != 1:
                    result['status'] = constants.ERROR
                    result['message'] = error_message
                else:
                    brain = brains[0]
                    url = brain.getURL()
                    if brain.portal_type in use_view_action:
                        url = url + '/view'
                    result['redirect_url'] = url
            elif status == constants.ERROR:
                result['message'] = error_message
        else:
            result['status'] = constants.ERROR
            result['message'] = error_message
        request.response.setHeader('Content-Type',
                                   'application/json; charset=utf-8')
        return json.dumps(result)
