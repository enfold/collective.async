# -*- coding: utf-8 -*-
import uuid
from . import constants
from BTrees.OOBTree import OOBTree
from persistent.mapping import PersistentMapping
from plone.api import portal as portal_api
from zope.annotation.interfaces import IAnnotations


def add_task_storage():
    portal = portal_api.get()
    annotations = IAnnotations(portal)
    if constants.TASKS_STORAGE_ID not in annotations:
        annotations[constants.TASKS_STORAGE_ID] = OOBTree()


def get_task_storage():
    portal = portal_api.get()
    annotations = IAnnotations(portal)
    if constants.TASKS_STORAGE_ID not in annotations:
        annotations[constants.TASKS_STORAGE_ID] = OOBTree()
    return annotations[constants.TASKS_STORAGE_ID]


def register_task(**kwargs):
    task_id = uuid.uuid4().hex
    record = PersistentMapping(kwargs)
    record['status'] = constants.PROCESSING
    storage = get_task_storage()
    storage[task_id] = record
    return task_id


def update_task(task_id, **kwargs):
    storage = get_task_storage()
    record = storage[task_id]
    record.update(kwargs)


def remove_task(task_id):
    storage = get_task_storage()
    del storage[task_id]


def has_task(task_id):
    storage = get_task_storage()
    return task_id in storage


def get_task(task_id):
    storage = get_task_storage()
    return storage.get(task_id)
