# -*- coding: utf-8 -*-
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.interface import Interface, Attribute
from zope.interface.interfaces import IObjectEvent


class ICollectiveAsyncLayer(IDefaultBrowserLayer):
    pass


class IAsyncBeforeAdd(IObjectEvent):
    """ Event that will be fired before adding an async add task
    """


class IAsyncBeforeEdit(IObjectEvent):
    """ Event that will be fired before adding an async edit task
    """


class IAsyncBeforePaste(IObjectEvent):
    """ Event that will be fired before adding an async paste task
    """


class IAsyncBeforeRename(IObjectEvent):
    """ Event that will be fired before adding an async rename task
    """

    newid = Attribute("The new id for the object.")
    newtitle = Attribute("The new title for the object.")


class IAsyncBeforeDelete(IObjectEvent):
    """ Event that will be fired before adding an async delete task
    """


class AsyncValidationFailed(Exception):
    """ Validation failed before async task was sent """
