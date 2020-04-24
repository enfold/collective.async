# -*- coding: utf-8 -*-
import collective.celery
import transaction
import traceback
import zope.event
import zope.lifecycleevent
from . import constants
from . import utils
from AccessControl import Unauthorized
from Acquisition import aq_inner
from Acquisition import aq_parent
from plone.api import content as content_api
from plone.dexterity import events as dexterity_events
from plone.dexterity import utils as dexterity_utils
from plone.uuid.interfaces import IUUID
from ZODB.POSException import ConflictError
from zope.container.interfaces import INameChooser


@collective.celery.task(name="colllective.async.add_object", bind=True)
def add_object(task, container, task_id):
    task_record = utils.get_task(task_id)
    obj = task_record["obj"]
    try:
        zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(obj))
        new_obj = dexterity_utils.addContentToContainer(container, obj)
        uuid = IUUID(new_obj)
        record_task_result.apply_async(
            [task_id, constants.SUCCESS], dict(obj=None, obj_uid=uuid)
        )
        transaction.commit()
    except ConflictError:
        retries = task.request.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            tb = traceback.format_exc()
            record_task_result.apply_async(
                [task_id, constants.ERROR],
                dict(obj=None, tb=tb),
                without_transaction=True,
            )
        raise
    except Exception as e:
        exc = str(e)
        tb = traceback.format_exc()
        record_task_result.apply_async(
            [task_id, constants.ERROR],
            dict(obj=None, message=exc, tb=tb),
            without_transaction=True,
        )
        raise


def add_description_func(task):
    context = content_api.get(UID=task['context'])
    obj = task.get("obj")
    folder_url = ""
    if context:
        folder_url = context.absolute_url()
    msg = (
        "<span>Adding '<strong>{title}</strong>' to "
        "<a href='{url}'>{url}</a></span>"
    ).format(title=obj.title, url=folder_url)
    return msg


def add_error_func(task):
    context = content_api.get(UID=task['context'])
    obj = task.get("obj")
    folder_url = ""
    if context:
        folder_url = context.absolute_url()
    msg = (
        "<span>An error occurred when trying to add '"
        "<strong>{title}</strong>' to <a href='{url}'>{url}</a></span>"
    ).format(title=obj.title, url=folder_url)
    return msg


def add_success_func(task):
    obj_uid = task.get("obj_uid")
    obj_url = ""
    if obj_uid:
        obj = content_api.get(UID=obj_uid)
        obj_url = obj.absolute_url()

    msg = (
        "<p>Your new content has been created, you can visit it "
        "from here: <a href='{url}'>{url}</a></p>"
    ).format(url=obj_url)
    return msg


utils.register_action(constants.ADD,
                      add_description_func,
                      add_success_func,
                      add_error_func)


@collective.celery.task(name="collective.async.finish_edit", bind=True)
def finish_edit(task, obj, task_id):
    task_record = utils.get_task(task_id)
    changes = task_record["changes"]
    descriptions = []
    for interface, names in changes:
        interface = dexterity_utils.resolveDottedName(interface)
        descriptions.append(zope.lifecycleevent.Attributes(interface, *names))
    try:
        zope.event.notify(
            zope.lifecycleevent.ObjectModifiedEvent(obj, *descriptions)
        )
        zope.event.notify(dexterity_events.EditFinishedEvent(obj))
        record_task_result.apply_async([task_id, constants.SUCCESS], dict())
        transaction.commit()
    except ConflictError:
        retries = task.request.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            tb = traceback.format_exc()
            record_task_result.apply_async(
                [task_id, constants.ERROR],
                dict(tb=tb),
                without_transaction=True,
            )
        raise
    except Exception as e:
        exc = str(e)
        tb = traceback.format_exc()
        record_task_result.apply_async(
            [task_id, constants.ERROR],
            dict(message=exc, tb=tb),
            without_transaction=True,
        )
        raise


def edit_description_func(task):
    item_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        item_url = context.absolute_url()
    msg = (
        "<span>Saving changes to <a href='{url}'>{url}</a></span>"
    ).format(url=item_url)
    return msg


def edit_error_func(task):
    item_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        item_url = context.absolute_url()
    msg = (
        "<span>An error occurred when trying to save changes to "
        "<a href='{url}'>{url}</a></span>"
    ).format(url=item_url)
    return msg


def edit_success_func(task):
    item_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        item_url = context.absolute_url()
    msg = (
        "<p>Changes to <a href='{url}'>{url}</a> have been saved.</p>"
    ).format(url=item_url)
    return msg


utils.register_action(constants.EDIT,
                      edit_description_func,
                      edit_success_func,
                      edit_error_func)


@collective.celery.task(name="collective.async.record_task_results")
def record_task_result(task_id, status, **kwargs):
    utils.update_task(task_id, status=status, **kwargs)


@collective.celery.task(name="collective.async.delete", bind=True)
def delete(task, parent, obj_id, obj_title, task_id):
    try:
        parent.manage_delObjects(obj_id)
        record_task_result.apply_async(
            [task_id, constants.SUCCESS], dict(title=obj_title),
        )
        transaction.commit()
    except ConflictError:
        retries = task.request.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            tb = traceback.format_exc()
            record_task_result.apply_async(
                [task_id, constants.ERROR],
                dict(title=obj_title, tb=tb),
                without_transaction=True,
            )
        raise
    except Unauthorized:
        msg = u"You are not authorized to delete this object."
        record_task_result.apply_async(
            [task_id, constants.ERROR],
            dict(title=obj_title, message=msg),
            without_transaction=True,
        )
        raise
    except Exception as e:
        exc = str(e)
        tb = traceback.format_exc()
        record_task_result.apply_async(
            [task_id, constants.ERROR],
            dict(title=obj_title, message=exc, tb=tb),
            without_transaction=True,
        )
        raise


def delete_description_func(task):
    id = task.get("id", "")
    folder_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        folder_url = context.absolute_url()
    msg = (
        "<span>Deleting item with id '<strong>{id}</strong>' "
        "from <a href='{url}'>{url}</a></span>"
    ).format(id=id, url=folder_url)
    return msg


def delete_error_func(task):
    id = task.get("id", "")
    folder_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        folder_url = context.absolute_url()
    msg = (
        "<span>An error occurred when trying to delete item with id '"
        "<strong>{id}</strong>' from <a href='{url}'>{url}</a></span>"
    ).format(id=id, url=folder_url)
    return msg


def delete_success_func(task):
    id = task.get("id", "")
    title = task.get("title", "")
    folder_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        folder_url = context.absolute_url()
    msg = (
        "<span>Item with id '<strong>{id}</strong>' and title "
        "'<strong>{title}</strong>' has been deleted from "
        "<a href='{url}'>{url}</a></span>"
    ).format(id=id, title=title, url=folder_url)
    return msg


utils.register_action(constants.DELETE,
                      delete_description_func,
                      delete_success_func,
                      delete_error_func)


@collective.celery.task(name="collective.async.rename", bind=True)
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
        record_task_result.apply_async(
            [task_id, constants.SUCCESS], dict(old_id=old_id)
        )
        transaction.commit()
    except ConflictError:
        retries = task.request.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            tb = traceback.format_exc()
            record_task_result.apply_async(
                [task_id, constants.ERROR],
                dict(tb=tb),
                without_transaction=True,
            )
        raise
    except Unauthorized:
        msg = u"You are not authorized to rename this object."
        record_task_result.apply_async(
            [task_id, constants.ERROR],
            dict(message=msg),
            without_transaction=True,
        )
        raise
    except Exception as e:
        exc = str(e)
        tb = traceback.format_exc()
        record_task_result.apply_async(
            [task_id, constants.ERROR],
            dict(message=exc, tb=tb),
            without_transaction=True,
        )
        raise


def rename_description_func(task):
    item_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        item_url = context.absolute_url()
    msg = ("<span>Renaming item <a href='{url}'>{url}</a>.").format(
        url=item_url
    )
    old_title = task.get("old_title")
    new_title = task.get("new_title")
    if old_title != new_title:
        msg += " New title: <strong>%s</strong>." % new_title
    old_id = task.get("old_id")
    new_id = task.get("new_id")
    if old_id != new_id:
        msg += " New ID: <strong>%s</strong>." % new_id
    msg += "</span>"
    return msg


def rename_error_func(task):
    item_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        item_url = context.absolute_url()
    msg = (
        "<span>An error occurred when trying to rename item "
        "<a href='{url}'>{url}</a>."
    ).format(url=item_url)
    old_title = task.get("old_title")
    new_title = task.get("new_title")
    if old_title != new_title:
        msg += " The new title was: <strong>%s</strong>." % new_title
    old_id = task.get("old_id")
    new_id = task.get("new_id")
    if old_id != new_id:
        msg += " The new ID was: <strong>%s</strong>." % new_id
    msg += "</span>"
    return msg


def rename_success_func(task):
    context = content_api.get(UID=task['context'])
    item_url = ""
    if context:
        item_url = context.absolute_url()
    msg = (
        "<p>Item <a href='{url}'>{url}</a> has been successfully "
        "renamed.</p>"
    ).format(url=item_url)
    old_title = task.get("old_title")
    new_title = task.get("new_title")
    if old_title != new_title:
        msg += (
            "<p>Old title: <strong>{old_title}</strong>. "
            "New title: <strong>{new_title}</strong>.</p>"
        ).format(old_title=old_title, new_title=new_title)
    old_id = task.get("old_id")
    new_id = task.get("new_id")
    if old_id != new_id:
        msg += (
            "<p>Old ID: <strong>{old_id}</strong>. "
            "New ID: <strong>{new_id}</strong>.</p>"
        ).format(old_id=old_id, new_id=new_id)
    return msg


utils.register_action(constants.RENAME,
                      rename_description_func,
                      rename_success_func,
                      rename_error_func)


@collective.celery.task(name="collective.async.paste", bind=True)
def paste(task, obj, cp, task_id):
    try:
        obj.manage_pasteObjects(cp)
        record_task_result.apply_async([task_id, constants.SUCCESS], dict())
    except ConflictError:
        retries = task.request.retries + 1
        max_retries = task.max_retries
        if max_retries is not None and retries > max_retries:
            tb = traceback.format_exc()
            record_task_result.apply_async(
                [task_id, constants.ERROR],
                dict(tb=tb),
                without_transaction=True,
            )
        raise
    except Unauthorized:
        message = u"You are not authorized to paste here"
        record_task_result.apply_async(
            [task_id, constants.ERROR],
            dict(message=message),
            without_transaction=True,
        )
        raise
    except Exception as e:
        exc = str(e)
        tb = traceback.format_exc()
        record_task_result.apply_async(
            [task_id, constants.ERROR],
            dict(message=exc, tb=tb),
            without_transaction=True,
        )
        raise


def paste_description_func(task):
    item_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        item_url = context.absolute_url()
    msg = (
        "<span>Pasting item in <a href='{url}'>{url}</a></span>"
    ).format(url=item_url)
    return msg


def paste_error_func(task):
    item_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        item_url = context.absolute_url()
    msg = (
        "<span>There was an error when pasting item in "
        "<a href='{url}'>{url}</a></span>"
    ).format(url=item_url)
    return msg


def paste_success_func(task):
    item_url = ""
    context = content_api.get(UID=task['context'])
    if context:
        item_url = context.absolute_url()
    msg = (
        "<p>Content was pasted at <a href='{url}'>{url}</a></p>"
    ).format(url=item_url)
    return msg


utils.register_action(constants.PASTE,
                      paste_description_func,
                      paste_success_func,
                      paste_error_func)