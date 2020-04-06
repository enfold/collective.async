# -*- coding: utf-8 -*-
from . import utils


def install_steps(context):
    if context.readDataFile('collective-async-install.txt') is None:
        return
    utils.add_task_storage()