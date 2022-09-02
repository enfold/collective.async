# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

version = "1.0.0"

setup(name='collective.async',
      version=version,
      description="",
      long_description='',
      # Get more strings from
      # https://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          "Framework :: Plone",
          "Framework :: Plone :: 5.0",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.7",
      ],
      keywords='',
      author='Enfold Systems Inc.',
      author_email='info@enfoldsystems.com',
      url='http://www.enfoldsystems.com',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'collective.celery',
          'plone.api',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone

      [celery_tasks]
      collective_async = collective.async.tasks

      [console_scripts]
      cleanup_task_results = collective.async.cleanup:main
      """,
      )
