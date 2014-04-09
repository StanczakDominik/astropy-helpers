import os
import shutil
import subprocess as sp
import sys

from setuptools.sandbox import run_setup

import pytest

PACKAGE_DIR = os.path.dirname(__file__)


def run_cmd(cmd, args, path=None):
    """
    Runs a shell command with the given argument list.  Changes directory to
    ``path`` if given, otherwise runs the command in the current directory.

    Returns a 3-tuple of (stdout, stderr, exit code)
    """

    if path is not None:
        # Transparently support py.path objects
        path = str(path)

    p = sp.Popen([cmd] + list(args), stdout=sp.PIPE, stderr=sp.PIPE,
                 cwd=path)
    streams = tuple(s.decode('latin1').strip() for s in p.communicate())
    return streams + (p.returncode,)


@pytest.fixture(scope='function', autouse=True)
def reset_distutils_log():
    """
    This is a setup/teardown fixture that ensures the log-level of the
    distutils log is always set to a default of WARN, since different
    settings could affect tests that check the contents of stdout.
    """

    from distutils import log
    log.set_threshold(log.WARN)


@pytest.fixture
def package_template(tmpdir, request):
    """Create a copy of the package_template repository (containing the package
    template) in a tempdir and change directories to that temporary copy.

    Also ensures that any previous imports of the test package are unloaded
    from `sys.modules`.
    """

    tmp_package = tmpdir.join('package_template')
    shutil.copytree(os.path.join(PACKAGE_DIR, 'package_template'),
                    str(tmp_package))

    old_cwd = os.getcwd()

    # Before changing directores import the local ah_boostrap module so that it
    # is tested, and *not* the copy that happens to be included in the test
    # package

    import ah_bootstrap

    # This is required to prevent the multiprocessing atexit bug
    import multiprocessing

    os.chdir(str(tmp_package))

    if 'packagename' in sys.modules:
        del sys.modules['packagename']

    old_astropy_helpers = None
    if 'astropy_helpers' in sys.modules:
        # Delete the astropy_helpers that was imported by running the tests so
        # as to not confuse the astropy_helpers that will be used in testing
        # the package
        old_astropy_helpers = sys.modules['astropy_helpers']
        del sys.modules['astropy_helpers']

    if '' in sys.path:
        sys.path.remove('')

    sys.path.insert(0, '')

    def finalize(old_cwd=old_cwd, old_astropy_helpers=old_astropy_helpers):
        os.chdir(old_cwd)
        sys.modules['astropy_helpers'] = old_astropy_helpers

    request.addfinalizer(finalize)

    return tmp_package


TEST_PACKAGE_SETUP_PY = """\
#!/usr/bin/env python

from setuptools import setup

setup(name='astropy-helpers-test', version='0.0',
      packages=['_astropy_helpers_test_'],
      zip_safe=False)
"""


@pytest.fixture
def testpackage(tmpdir):
    """
    This fixture creates a simplified package called _astropy_helpers_test_
    used primarily for testing ah_boostrap, but without using the
    astropy_helpers package directly and getting it confused with the
    astropy_helpers package already under test.
    """

    source = tmpdir.mkdir('testpkg')

    with source.as_cwd():
        source.mkdir('_astropy_helpers_test_')
        source.ensure('_astropy_helpers_test_', '__init__.py')
        source.join('setup.py').write(TEST_PACKAGE_SETUP_PY)

        # Make the new test package into a git repo
        run_cmd('git', ['init'])
        run_cmd('git', ['add', '--all'])
        run_cmd('git', ['commit', '-m', 'test package'])

    return source


# Ugly workaround
# Note sure exactly why, but there is some weird interaction between setuptools
# entry points and the way run_setup messes with sys.modules that causes this
# module go out out of scope during the tests; importing it here prevents that
import setuptools.py31compat
