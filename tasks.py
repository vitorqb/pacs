import os
from functools import wraps
from invoke import task
from invoke.tasks import Context
from invoke.runners import Result
from contextlib import contextmanager


FUNCTIONAL_TESTS_PATH = "functional_tests.py"
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
MANAGE_PATH = os.path.join(ROOT_DIR, "manage.py")


#
# Set Up
#
class PacsContext:
    """ Wrapper around invoke.context.Context to provide usefull apis to us. """
    _context: Context

    def __init__(self, context: Context):
        self._context = context

    def run(self, cmd: str, pty: bool = False) -> Result:
        return self._context.run(cmd)

    @contextmanager
    def cd(self, dir_: str):
        yield self._context.cd(dir_)

    def run_manage(self, cmd: str, pty: bool = False):
        """ Runs a django management command """
        self.run(f"python {MANAGE_PATH} {cmd}", pty)


def pacstask(f):
    """ Same as invoke.task but parses a PacsContext instead of a
    Context """
    @wraps(f)
    def wrapped(c, *args, **kwargs):
        pacs_context = PacsContext(c)
        return f(pacs_context, *args, **kwargs)

    return task(wrapped)


#
# Reusable tasks
#
def _run_pytest(c, opts):
    c.run(f"pytest {opts} --cov=.", pty=True)


def _populate_db(c):
    for x in ["populate_accounts", "populate_currencies"]:
        c.run_manage(x)


#
# Tasks
#
@pacstask
def unit_test(c, opts=""):
    """ Calls pytest for all unit tests. """
    _run_pytest(c, f"--ignore={FUNCTIONAL_TESTS_PATH} {opts}")


@pacstask
def func_test(c, opts=""):
    """ Calls functional tests for python """
    _run_pytest(c, f"{FUNCTIONAL_TESTS_PATH} {opts}")


@pacstask
def test(c, opts=""):
    """ Runs functional and unit tests """
    _run_pytest(c, f". {opts}")


@pacstask
def populate_db(c):
    """ Calls the management commands to populate the db """
    _populate_db(c)


@pacstask
def runserver(c):
    """ Runs the development server """
    _populate_db(c)
    c.run_manage("runserver_plus --print-sql", pty=True)


@pacstask
def migrate(c):
    """ Runs migrations """
    c.run_manage("migrate", pty=True)
