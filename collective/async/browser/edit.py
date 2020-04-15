# -*- coding: utf-8 -*-
from .. import constants
from .. import tasks
from .. import utils
from plone.dexterity.browser import edit
from plone.dexterity.i18n import MessageFactory as _
from plone.dexterity.interfaces import IDexterityEditForm
from plone.uuid.interfaces import IUUID
from plone.z3cform import layout
from z3c.form import form
from z3c.form import button
from zope.interface import classImplements


class AsyncEditForm(edit.DefaultEditForm):
    @button.buttonAndHandler(_(u"Save"), name="save")
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
        uuid = IUUID(content, 0)
        task_id = utils.register_task(
            action=constants.EDIT, changes=new_changes, context=uuid
        )
        tasks.finish_edit.apply_async([content, task_id], dict())
        utils.add_task_to_cookie(self.request, task_id)
        return self.request.response.redirect(content.absolute_url())


AsyncEditView = layout.wrap_form(AsyncEditForm)
classImplements(AsyncEditView, IDexterityEditForm)
