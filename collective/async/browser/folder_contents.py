# -*- coding: utf-8 -*-
import json
import zope.component
from plone.api import portal as portal_api
from plone.app.content.browser.contents import ContentsBaseAction
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class DeleteActionsView(ContentsBaseAction):

    def __call__(self):
        request = self.request
        selection = self.get_selection()
        if request.form.get('render') == 'yes':
            portal = portal_api.get()
            confirm_view = zope.component.getMultiAdapter(
                (portal, request),
                name='delete_confirmation_info'
            )
            catalog = portal_api.get_tool('portal_catalog')
            brains = catalog.searchResults(UID=selection, show_inactive=True)
            items = [b.getObject() for b in brains]
            request.response.setHeader(
                'Content-Type', 'application/json; charset=utf-8'
            )
            return json.dumps({
                'html': confirm_view(items)
            })
        else:
