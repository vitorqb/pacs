import os
import sys
from functools import partial
from invoke import task
from invoke.tasks import Context, Task
from invoke.runners import Result
from invoke.exceptions import Exit
from contextlib import contextmanager

import tempfile

FUNCTIONAL_TESTS_PATH = "functional_tests.py"
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
MANAGE_PATH = os.path.join(ROOT_DIR, "manage.py")
BUILD_SOURCES = [
    "accounts",
    "common",
    "currencies",
    "exchange_rate_fetcher",
    "invoke.yaml",
    "manage.py",
    "movements",
    "pacs",
    "pacs_auth",
    "reports",
    "requirements",
    "tasks.py"
]
DOCKER_CMD = os.environ.get("PACS_DOCKER_CMD", "docker")


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
    with c.prefix("export $(grep -v '^#' .env.test | xargs)"):
        c.run(f"pytest {opts} --cov=.", pty=True)


def _populate_db(c):
    for x in ["populate_accounts", "populate_currencies"]:
        c.run_manage(x)


def _new_venv(c, path, requirements_file="requirements/development.txt"):
    c.run(f'python -m venv "{path}"')
    with c.prefix(f'source "{path}/bin/activate"'):
        c.run(f'pip install --upgrade pip')
        c.run(f'pip install -r {requirements_file}')


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


@pacstask(help={"dev": "Install dev requirements", "deploy": "Install deploy requirements"})
def requirements(c, dev=False, deploy=False):
    """ Installs requirements for pacs """
    cmd = "pip install -r requirements/base_frozen.txt"

    if dev:
        cmd += " -r requirements/development.txt"

    if deploy:
        cmd += " -r requirements/deploy.txt"

    c.run(cmd, pty=True)


@pacstask(help={"dep_name": "Name of the dependency"})
def add_base_requirement(c, dep_name):
    """ Adds a base requirement for pacs by installing the most recent
    dependency version compatible and adding it to
    `base_frozen.txt`"""
    tmp_file_name = tempfile.NamedTemporaryFile(suffix=".txt").name
    c.run(f"rm -rf {tmp_file_name}")
    c.run(f"cp requirements/base_frozen.txt {tmp_file_name}")
    c.run(f"echo '{dep_name}' >> '{tmp_file_name}'")
    c.run(f"pip install -r {tmp_file_name}")
    c.run(f"pip freeze | grep -P '^{dep_name}==' | tee --append requirements/base_frozen.txt")
    c.run(f"echo '{dep_name}' | tee --append requirements/base.txt")
    c.run(f"rm -rf {tmp_file_name}")

@pacstask()
def update_frozen_requirements(c):
    """ Updates the `base_frozen` file with the most up-to-date requirements"""
    venv_dir = tempfile.mkdtemp()
    _new_venv(c, venv_dir, "requirements/base.txt")
    with c.prefix(f'source "{venv_dir}/bin/activate"'):
        c.run(f"pip freeze | tee ./requirements/base_frozen.txt")


@pacstask()
def venv(c):
    """ Prepares virtualenv in "./venv" """
    c.run("rm -rf ./venv")
    _new_venv(c, "./venv")


@pacstask()
def unit_test(c, opts=""):
    """ Calls pytest for all unit tests. """
    opts += ' -m "not functional"'
    _run_pytest(c, opts)


@pacstask()
def func_test(c, opts=""):
    """ Calls functional tests for python """
    opts += ' -m "functional"'
    _run_pytest(c, opts)


@pacstask()
def test(c, opts=""):
    """ Runs functional and unit tests """
    _run_pytest(c, f"{opts}")


@pacstask()
def populate_db(c):
    """ Calls the management commands to populate the db """
    _populate_db(c)


@pacstask()
def runserver(c):
    """ Runs the development server """
    _populate_db(c)
    c.run_manage("runserver_plus --print-sql 0.0.0.0:8000", pty=True)


@pacstask()
def migrate(c, no_input=False):
    """ Runs migrations """
    cmd = "migrate" + (" --no-input" if no_input else "")
    c.run_manage(cmd, pty=True)


@pacstask()
def makemigrations(c, no_input=False):
    """ Runs makemigrations """
    cmd = "makemigrations" + (" --no-input" if no_input else "")
    c.run_manage(cmd, pty=True)

@pacstask()
def collectstatic(c, no_input=False):
    """ Runs collectstatic """
    cmd = "collectstatic" + (" --no-input" if no_input else "")
    c.run_manage(cmd, pty=True)

@pacstask()
def build(c, build_dir="./build", dist_dir="./dist"):
    version = c.run("git describe --tags").stdout.strip()
    c.run(f"rm -rf {build_dir}")
    c.run(f"mkdir -p {build_dir}")
    c.run(f"mkdir -p {dist_dir}")
    for x in BUILD_SOURCES:
        c.run(f"cp -r {x} {build_dir}/{x}")
    for x in ["__pycache__", ".mypy_cache", "tests"]:
        c.run(f'find build -depth -type d -name "{x}" -exec rm -rf '+'"{}" \;')
    with c.cd(build_dir):
        c.run(f"tar -vzcf pacs-{version}.tar.gz **")
    c.run(f"mv {build_dir}/pacs-{version}.tar.gz {dist_dir}/pacs-{version}.tar.gz")
    c.run(f"{DOCKER_CMD} build -t 'pacs:{version}' --build-arg 'VERSION={version}' -f docker/Dockerfile .")
