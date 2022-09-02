# -*- coding: utf-8 -*-
import argparse
import logging
import os
import sys
import transaction
import Zope2
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import system
from collective.async import utils
from datetime import timedelta
from plone.app.theming.interfaces import IThemingLayer
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.event import notify
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from zope.traversing.interfaces import BeforeTraverseEvent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log-file')
    parser.add_argument('--plone-site')
    parser.add_argument('--days-to-keep', type=int, default=1)
    parser.add_argument('config_file')

    args = parser.parse_args()
    logfile = args.log_file
    logger = logging.getLogger()
    if logfile:
        handler = logging.FileHandler(logfile)
    else:
        handler = logging.StreamHandler(stream=sys.stdout)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    config_file = args.config_file

    old_argv = sys.argv
    sys.argv = ['']

    os.environ['ZOPE_CONFIG'] = config_file
    app = Zope2.app()

    sys.argv = old_argv
    app = makerequest(app)
    setRequest(app.REQUEST)
    newSecurityManager(None, system)
    plone_site = args.plone_site and args.plone_site or 'Plone'
    site = app.unrestrictedTraverse(plone_site)
    setSite(site=site)
    request = site.REQUEST
    request['PARENTS'] = [site, app]
    alsoProvides(request, IThemingLayer)
    site.clearCurrentSkin()
    site.setupCurrentSkin(request)
    notify(BeforeTraverseEvent(site, request))
    setRequest(request)
    days = args.days_to_keep
    utils.cleanup_tasks(timedelta(days=days))
    transaction.commit()
