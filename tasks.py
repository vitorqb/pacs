import os
from functools import partial
from invoke import task
from invoke.tasks import Context, Task
from invoke.runners import Result
from invoke.exceptions import Exit
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

    def run(self, cmd: str, pty: bool = False, warn: bool = False) -> Result:
        return self._context.run(cmd, pty=pty, warn=warn)

    @contextmanager
    def cd(self, dir_: str):
        with self._context.cd(dir_):
            yield

    @contextmanager
    def prefix(self, cmd: str):
        with self._context.prefix(cmd):
            yield

    def run_manage(self, cmd: str, pty: bool = False):
        """ Runs a django management command """
        self.run(f"python {MANAGE_PATH} {cmd}", pty=pty)


class PacsTask(Task):
    """ We need to subclass otherwise invoke don't detect that it is a Task.
    We just want to adapt __call__ so that it uses PacsContext instead of
    Context. """
    def __call__(self, context: Context, *args, **kwargs):
        """ Converts the context into a PacsContext """
        result = self.body(PacsContext(context), *args, **kwargs)
        self.times_called += 1
        return result


pacstask = partial(task, klass=PacsTask)


#
# Reusable tasks
#
def _run_pytest(c, opts):
    c.run(f"pytest {opts} --cov=.", pty=True)


def _populate_db(c):
    for x in ["populate_accounts", "populate_currencies"]:
        c.run_manage(x)


def _new_venv(c, path):
    c.run(f'python -m venv "{path}"')
    with c.prefix(f'source "{path}/bin/activate"'):
        c.run(f'pip install --upgrade pip')
        c.run(f'pip install -r requirements/development.txt')


#
# Tasks
#
@pacstask(
    help={
        "path": "The path to the virtualenv.",
        "force": "If set to true, whatever is in path is removed before."
    }
)
def prepare_virtualenv(c, path, force=False):
    """ Prepares a virtualenv in a path """
    path_exists = c.run(f'[ -d "{path}" ] || [ -f "{path}" ]', warn=True).ok
    if path_exists:
        if force is not True:
            raise Exit(f"Path '{path}' exists and force is set to False!")
        else:
            c.run(f'rm -rf "{path}"')
    _new_venv(c, path)


@pacstask()
def venv(c):
    """ Prepares virtualenv in "./venv" """
    c.run("rm -rf ./venv")
    _new_venv(c, "./venv")


@pacstask()
def unit_test(c, opts=""):
    """ Calls pytest for all unit tests. """
    _run_pytest(c, f"--ignore={FUNCTIONAL_TESTS_PATH} {opts}")


@pacstask()
def func_test(c, opts=""):
    """ Calls functional tests for python """
    _run_pytest(c, f"{FUNCTIONAL_TESTS_PATH} {opts}")


@pacstask()
def test(c, opts=""):
    """ Runs functional and unit tests """
    _run_pytest(c, f". {opts}")


@pacstask()
def populate_db(c):
    """ Calls the management commands to populate the db """
    _populate_db(c)


@pacstask()
def runserver(c):
    """ Runs the development server """
    _populate_db(c)
    c.run_manage("runserver_plus --print-sql", pty=True)


@pacstask()
def migrate(c):
    """ Runs migrations """
    c.run_manage("migrate", pty=True)


@pacstask()
def makemigrations(c):
    """ Runs makemigrations """
    c.run_manage("makemigrations", pty=True)
