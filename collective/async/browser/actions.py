# -*- coding: utf-8 -*-
import json
import zope.component
from .. import constants
from .. import tasks
from .. import utils
from AccessControl import getSecurityManager
from AccessControl import Unauthorized
from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent
from plone.api import user as user_api
from plone.app.content.browser import actions as plone_actions
from plone.registry.interfaces import IRegistry
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone import utils as plone_utils
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import button
from zope.publisher.browser import BrowserView


class DeleteConfirmationForm(plone_actions.DeleteConfirmationForm):

    @button.buttonAndHandler(_(u'Delete'), name='Delete')
    def handle_delete(self, action):
        context = self.context
        request = self.request
        inner = aq_inner(context)
        parent = aq_parent(inner)
        title = plone_utils.safe_unicode(context.Title())
        if context.aq_chain == inner.aq_chain:
            pass
            task_id = utils.register_task()
            tasks.delete.apply_async([parent, context.getId(), title, task_id],
                                     dict())
            url = parent.absolute_url() + '/wait-for-delete?task_id=%s' % task_id
            return request.response.redirect(url)
        else:
            IStatusMessage(request).add(
                _(u'"${title}" has already been deleted',
                  mapping={u'title': title})
            )
            return request.response.redirect(parent.absolute_url())


class CheckForDelete(BrowserView):

    def __call__(self, *args, **kwargs):
        context = self.context
        if user_api.is_anonymous():
            raise Unauthorized
        request = self.request
        task_id = request.get('task_id')
        result = dict()
        error_message = u'Sorry, there was an error deleting your object.'
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
            elif status == constants.ERROR:
                result['message'] = task.get('message', error_message)
        else:
            result['message'] = error_message
            result['status'] = constants.ERROR
        request.response.setHeader('Content-Type',
                                   'application/json; charset=utf-8')
        return json.dumps(result)


class RenameForm(plone_actions.RenameForm):

    @button.buttonAndHandler(_(u'Rename'), name='Rename')
    def handle_rename(self, action):
        data, errors = self.extractData()
        if errors:
            return
        context = self.context
        parent = aq_parent(aq_inner(context))
        sm = getSecurityManager()
        if not sm.checkPermission('Copy or Move', parent):
            raise Unauthorized(_(u'Permission denied to rename ${title}.',
                                 mapping={u'title': context.title}))
        task_id = utils.register_task()
        tasks.rename.apply_async([context, data['new_id'], data['new_title'],
                                  task_id], dict())
        url = parent.absolute_url() + '/wait-for-rename?task_id=%s' % task_id
        return self.request.response.redirect(url)


class CheckForRename(BrowserView):

    def __call__(self, *args, **kwargs):
        context = self.context
        if user_api.is_anonymous():
            raise Unauthorized
        request = self.request
        task_id = request.get('task_id')
        result = dict()
        error_message = u'Sorry, there was an error renaming your object.'
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
            elif status == constants.ERROR:
                result['message'] = task.get('message', error_message)
        else:
            result['message'] = error_message
            result['status'] = constants.ERROR
        request.response.setHeader('Content-Type',
                                   'application/json; charset=utf-8')
        return json.dumps(result)


class ObjectPasteView(plone_actions.ObjectPasteView):

    def do_action(self):
        context = self.context
        request = self.request
        if not context.cb_dataValid():
            return self.do_redirect(
                self.canonical_object_url,
                _(u'Copy or cut one or more items to paste.'),
                'error'
            )
        task_id = utils.register_task()

        tasks.paste.apply_async([context, request['__cp'], task_id],
                                dict())
        url = context.absolute_url() + '/wait-for-paste?task_id=%s' % task_id
        return request.response.redirect(url)


class CheckForPaste(BrowserView):

    def __call__(self, *args, **kwargs):
        context = self.context
        if user_api.is_anonymous():
            raise Unauthorized
        request = self.request
        task_id = request.get('task_id')
        result = dict()
        error_message = u'Sorry, there was an error pasting your object.'
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
            elif status == constants.ERROR:
                result['message'] = task.get('message', error_message)
        else:
            result['message'] = error_message
            result['status'] = constants.ERROR
        request.response.setHeader('Content-Type',
                                   'application/json; charset=utf-8')
        return json.dumps(result)
