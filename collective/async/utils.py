# -*- coding: utf-8 -*-
import json
import logging
import uuid
from . import constants
from datetime import datetime
from BTrees.OOBTree import OOBTree
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone.api import portal as portal_api
from plone.api import user as user_api
from zope.annotation.interfaces import IAnnotations

logger = logging.getLogger(__name__)


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
    now = datetime.now()
    user_id = user_api.get_current().getId()
    record = PersistentMapping(kwargs)
    record["status"] = constants.PROCESSING
    record["task_id"] = task_id
    record['timestamp'] = now
    record['seen'] = False
    record['user'] = user_id
    storage = get_task_storage()
    if 'users' not in storage:
        storage['users'] = OOBTree()
    if user_id not in storage['users']:
        storage['users'][user_id] = PersistentList()
    storage['users'][user_id].append(task_id)
    storage[task_id] = record
    return task_id


def get_taskids_for_user():
    user_id = user_api.get_current().getId()
    storage = get_task_storage()
    tasks = list()
    if user_id in storage.get('users', dict()):
        for taskid in storage['users'][user_id]:
            tasks.append(taskid)
    return tasks


def get_tasks_for_user():
    tasks = list()
    task_ids = get_taskids_for_user()
    for task_id in task_ids:
        task = get_task(task_id)
        tasks.append(task)
    return tasks


def get_ip_tasks_for_user():
    tasks = list()
    task_ids = get_taskids_for_user()
    for task_id in task_ids:
        task = get_task(task_id)
        if task["status"] == constants.PROCESSING:
            tasks.append(task)
    return tasks


def update_task(task_id, **kwargs):
    storage = get_task_storage()
    record = storage[task_id]
    record.update(kwargs)


def mark_task_seen(task_id):
    update_task(task_id, seen=True)


def remove_task(task_id):
    storage = get_task_storage()
    record = storage.get(task_id, None)
    if record is not None:
        if 'user' in record:
            user_id = record['user']
            storage['users'][user_id].remove(task_id)
        del storage[task_id]
        logger.info('Removed task %s' % task_id)
    else:
        logger.info('There is no task with id %s' % task_id)


def cleanup_tasks(cutoff):
    now = datetime.now()
    storage = get_task_storage()
    for task_id in list(storage.keys()):
        if task_id == 'users':
            continue
        task = storage[task_id]
        if 'timestamp' in task:
            delta = now - task['timestamp']
            if delta >= cutoff:
                remove_task(task_id)
        else:
            remove_task(task_id)


def has_task(task_id):
    storage = get_task_storage()
    return task_id in storage


def get_task(task_id):
    storage = get_task_storage()
    return storage.get(task_id)


_ACTIONS = dict()


def register_action(action, description_func, success_func, error_func):
    _ACTIONS[action] = {
        constants.DESCRIPTION_FUNC_KEY: description_func,
        constants.SUCCESS_FUNC_KEY: success_func,
        constants.ERROR_FUNC_KEY: error_func}


def _get_message(task, func_key):
    action = task[constants.ACTION_KEY]
    msg = ""
    func = _ACTIONS.get(action, {}).get(func_key, None)
    if func is not None:
        msg = func(task)
    return msg


def get_task_description(task):
    return _get_message(task, constants.DESCRIPTION_FUNC_KEY)


def get_task_success_message(task):
    return _get_message(task, constants.SUCCESS_FUNC_KEY)


def get_task_error_message(task):
    return _get_message(task, constants.ERROR_FUNC_KEY)
