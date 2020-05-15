# -*- coding: utf-8 -*-
from .interfaces import IAsyncBeforeAdd
from .interfaces import IAsyncBeforeEdit
from .interfaces import IAsyncBeforePaste
from .interfaces import IAsyncBeforeRename
from .interfaces import IAsyncBeforeDelete
from zope.component.interfaces import ObjectEvent
from zope.interface import implements


class AsyncBeforeAdd(ObjectEvent):
    """An 'add' task will be created"""

    implements(IAsyncBeforeAdd)


class AsyncBeforeEdit(ObjectEvent):
    """An 'edit' task will be created"""

    implements(IAsyncBeforeEdit)


class AsyncBeforePaste(ObjectEvent):
    """A 'paste' task will be created"""

    implements(IAsyncBeforePaste)


class AsyncBeforeRename(ObjectEvent):
    """A 'rename' task will be created"""

    implements(IAsyncBeforeRename)

    def __init__(self, object, newid, newtitle):
        ObjectEvent.__init__(self, object)
        self.newid = newid
        self.newtitle = newtitle


class AsyncBeforeDelete(ObjectEvent):
    """An 'delete' task will be created"""

    implements(IAsyncBeforeDelete)
