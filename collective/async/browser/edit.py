# -*- coding: utf-8 -*-
import zope.component
from .. import constants
from .. import events
from .. import tasks
from .. import utils
from AccessControl import Unauthorized
from Acquisition import aq_base
from plone.dexterity.browser import edit
from plone.dexterity.events import EditCancelledEvent
from plone.dexterity.i18n import MessageFactory as _
from plone.dexterity.interfaces import IDexterityEditForm
from plone.registry.interfaces import IRegistry
from plone.uuid.interfaces import IUUID
from plone.z3cform import layout
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import form
from z3c.form import button
from zope.event import notify
from zope.interface import classImplements


class AsyncEditForm(edit.DefaultEditForm):
    success_message = _(u"Changes will be saved")

    @button.buttonAndHandler(_(u"Save"), name="save")
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorMessage
            return

        try:
            notify(events.AsyncBeforeEdit(self.context))
        except Unauthorized:
            IStatusMessage(self.request).add(
                _(u"You are not authorized to edit this element.")
            )
            return

        content = self.getContent()
        changes = form.applyChanges(self, content, data)
        new_changes = list()
        for interface, names in changes.items():
            new_changes.append((interface.__identifier__, names))
        uuid = IUUID(content, 0)
        task_id = utils.register_task(
            action=constants.EDIT, changes=new_changes, context=uuid
        )
        tasks.finish_edit.apply_async([content, task_id], dict())
        utils.add_task_to_cookie(self.request, task_id)
        IStatusMessage(self.request).addStatusMessage(
            self.success_message, "info"
        )

        url = content.absolute_url()
        portal_type = getattr(aq_base(content), "portal_type", None)
        registry = zope.component.getUtility(IRegistry)
        use_view_action = registry.get(
            "plone.types_use_view_action_in_listings", [])
        if portal_type in use_view_action:
            url = url + '/view'

        return self.request.response.redirect(url)

    @button.buttonAndHandler(_(u"Cancel"), name="cancel")
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(
            _(u"Edit cancelled"), "info"
        )
        self.request.response.redirect(self.nextURL())
        notify(EditCancelledEvent(self.context))


AsyncEditView = layout.wrap_form(AsyncEditForm)
classImplements(AsyncEditView, IDexterityEditForm)
