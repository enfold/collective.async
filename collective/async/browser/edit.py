# -*- coding: utf-8 -*-
import json
import zope.component
from .. import constants
from .. import tasks
from .. import utils
from AccessControl import Unauthorized
from Acquisition import aq_base
from plone.api import user as user_api
from plone.dexterity.browser import edit
from plone.dexterity.i18n import MessageFactory as _
from plone.dexterity.interfaces import IDexterityEditForm
from plone.registry.interfaces import IRegistry
from plone.z3cform import layout
from z3c.form import form
from z3c.form import button
from zope.publisher.browser import BrowserView
from zope.interface import classImplements


class AsyncEditForm(edit.DefaultEditForm):

    @button.buttonAndHandler(_(u'Save'), name='save')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorMessage
            return
        content = self.getContent()
        changes = form.applyChanges(self, content, data)
        new_changes = list()
        for interface, names in changes.items():
            new_changes.append((interface.__identifier__, names))
        task_id = utils.register_task(changes=new_changes)
        tasks.finish_edit.apply_async([content, task_id], dict())
        url = content.absolute_url() + '/wait-for-edit?task_id=%s' % task_id
        return self.request.response.redirect(url)


AsyncEditView = layout.wrap_form(AsyncEditForm)
classImplements(AsyncEditView, IDexterityEditForm)


class CheckForEdit(BrowserView):

    def __call__(self, *args, **kwargs):
        context = self.context
        if user_api.is_anonymous():
            raise Unauthorized
        request = self.request
        task_id = request.get('task_id')
        result = dict()
        if utils.has_task(task_id):
            task = utils.get_task(task_id)
            result['status'] = status = task['status']
            if status == constants.SUCCESS:
                url = context.absolute_url()
                portal_type = getattr(aq_base(context), 'portal_type', None)
                registry = zope.component.getUtility(IRegistry)
                use_view_action = registry.get(
                    'plone.types_use_view_action_in_listings', [])
                if portal_type in use_view_action:
                    url = url + '/view'
                result['redirect_url'] = url
        else:
            result['message'] = u'Sorry, there was an error editing your object.'
            result['status'] = constants.ERROR
        request.response.setHeader('Content-Type',
                                   'application/json; charset=utf-8')
        return json.dumps(result)
