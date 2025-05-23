#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2016 The Meson development team


import os, sys

if sys.version_info < (3, 7):
    raise SystemExit('ERROR: Tried to install Meson with an unsupported Python version: \n{}'
                     '\nMeson requires Python 3.7.0 or greater'.format(sys.version))

from setuptools import setup

scm_args = {}
HERE = os.path.dirname(__file__)
if os.path.exists(os.path.join(HERE, '.git')):
    try:
        import setuptools_scm
    except ModuleNotFoundError:
        pass
    else:
        sys.path.insert(0, HERE)
        from mesonbuild import coredata

        scheme = 'guess-next-dev' if 'rc' in coredata.version else 'release-branch-semver'
        scm_args = {'use_scm_version': {'version_scheme': scheme}}

data_files = []
if sys.platform != 'win32':
    # Only useful on UNIX-like systems
    data_files = [('share/man/man1', ['man/meson.1']),
                  ('share/polkit-1/actions', ['data/com.mesonbuild.install.policy'])]

setup(data_files=data_files,**scm_args)
