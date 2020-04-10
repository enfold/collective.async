# -*- coding: utf-8 -*-
import collective.celery
import transaction
import zope.event
import zope.lifecycleevent
from . import constants
from . import utils
from AccessControl import Unauthorized
from Acquisition import aq_inner
from Acquisition import aq_parent
from plone.dexterity import events as dexterity_events
from plone.dexterity import utils as dexterity_utils
from plone.uuid.interfaces import IUUID
from ZODB.POSException import ConflictError
from zope.container.interfaces import INameChooser


@collective.celery.task(name='colllective.async.add_object', bind=True)
def add_object(task, container, task_id):
    task_record = utils.get_task(task_id)
    obj = task_record['obj']
    try:
        zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(obj))
        new_obj = dexterity_utils.addContentToContainer(container, obj)
        uuid = IUUID(new_obj)
        record_task_result.apply_async([task_id, constants.SUCCESS],
                                       dict(obj=None, obj_uid=uuid))
        transaction.commit()
    except ConflictError:
        retries = task.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            record_task_result.apply_async([task_id, constants.ERROR],
                                           dict(obj=None),
                                           without_transaction=True)
        raise
    except Exception:
        record_task_result.apply_async([task_id, constants.ERROR],
                                       dict(obj=None), without_transaction=True)
        raise


@collective.celery.task(name='collective.async.finish_edit', bind=True)
def finish_edit(task, obj, task_id):
    task_record = utils.get_task(task_id)
    changes = task_record['changes']
    descriptions = []
    for interface, names in changes:
        interface = dexterity_utils.resolveDottedName(interface)
        descriptions.append(
            zope.lifecycleevent.Attributes(interface, *names)
        )
    try:
        zope.event.notify(
            zope.lifecycleevent.ObjectModifiedEvent(obj, *descriptions))
        zope.event.notify(dexterity_events.EditFinishedEvent(obj))
        record_task_result.apply_async([task_id, constants.SUCCESS],
                                       dict())
        transaction.commit()
    except ConflictError:
        retries = task.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            record_task_result.apply_async([task_id, constants.ERROR],
                                           dict(), without_transaction=True)
        raise
    except Exception:
        record_task_result.apply_async([task_id, constants.ERROR],
                                       dict(), without_transaction=True)
        raise


@collective.celery.task(name='collective.async.record_task_results')
def record_task_result(task_id, status, **kwargs):
    utils.update_task(task_id, status=status, **kwargs)


@collective.celery.task(name='collective.async.delete', bind=True)
def delete(task, parent, obj_id, obj_title, task_id):
    try:
        parent.manage_delObjects(obj_id)
        record_task_result.apply_async([task_id, constants.SUCCESS],
                                       dict(title=obj_title))
        transaction.commit()
    except ConflictError:
        retries = task.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            record_task_result.apply_async([task_id, constants.ERROR],
                                           dict(title=obj_title),
                                           without_transaction=True)
        raise
    except Unauthorized:
        msg = u'You are not authorized to delete this object.'
        record_task_result.apply_async([task_id, constants.ERROR],
                                       dict(title=obj_title,
                                            message=msg),
                                       without_transaction=True)
        raise
    except Exception:
        record_task_result.apply_async([task_id, constants.ERROR],
                                       dict(title=obj_title),
                                       without_transaction=True)
        raise


@collective.celery.task(name='collective.async.rename', bind=True)
def rename(task, obj, new_id, new_title, task_id):
    try:
        parent = aq_parent(aq_inner(obj))
        old_id = obj.getId()
        obj.title = new_title
        if old_id != new_id:
            new_id = INameChooser(parent).chooseName(new_id, obj)
            parent.manage_renameObjects([old_id], [str(new_id)])
        else:
            obj.reindexObject()

        transaction.savepoint(optimistic=True)
        zope.event.notify(zope.lifecycleevent.ObjectModifiedEvent(obj))
        record_task_result.apply_async([task_id, constants.SUCCESS],
                                       dict(old_id=old_id))
        transaction.commit()
    except ConflictError:
        retries = task.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            record_task_result.apply_async([task_id, constants.ERROR],
                                           dict(), without_transaction=True)
        raise
    except Unauthorized:
        msg = u'You are not authorized to rename this object.'
        record_task_result.apply_async([task_id, constants.ERROR],
                                       dict(message=msg),
                                       without_transaction=True)
        raise
    except Exception:
        record_task_result.apply_async([task_id, constants.ERROR],
                                       dict(), without_transaction=True)
        raise


@collective.celery.task(name='collective.async.paste', bind=True)
def paste(task, obj, cp, task_id):
    try:
        obj.manage_pasteObjects(cp)
        record_task_result.apply_async([task_id, constants.SUCCESS],
                                       dict())
    except ConflictError:
        retries = task.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            record_task_result.apply_async([task_id, constants.ERROR],
                                           dict(), without_transaction=True)
        raise
    except Unauthorized:
        message = u'You are not authorized to paste here'
        record_task_result.apply_async([task_id, constants.ERROR],
                                       dict(message=message),
                                       without_transaction=True)
        raise
    except Exception:
        record_task_result.apply_async([task_id, constants.ERROR],
                                       dict(), without_transaction=True)
        raise
