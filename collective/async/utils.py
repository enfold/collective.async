# -*- coding: utf-8 -*-
import json
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
    record["status"] = constants.PROCESSING
    record["task_id"] = task_id
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


def get_tasks_from_cookie(request):
    c_str = request.cookies.get(constants.IN_PROGRESS_COOKIE_NAME, "[]")
    try:
        ip_tasks = json.loads(c_str)
    except:
        ip_tasks = list()
    return ip_tasks


def add_task_to_cookie(request, task_id):
    ip_tasks = get_tasks_from_cookie(request)
    if task_id not in ip_tasks:
        ip_tasks.append(task_id)
    c_str = json.dumps(ip_tasks)
    request.response.setCookie(
        constants.IN_PROGRESS_COOKIE_NAME, c_str, path="/"
    )


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
