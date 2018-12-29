from invoke import task
import os


FUNCTIONAL_TESTS_PATH = "functional_tests.py"
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))


def run_pytest(c, opts):
    c.run(f"pytest {opts} --cov=.", pty=True)


def _populate_db(c):
    with c.cd(ROOT_DIR):
        c.run("python manage.py populate_accounts")
        c.run("python manage.py populate_currencies")


@task
def unit_test(c, opts=""):
    """ Calls pytest for all unit tests. """
    run_pytest(c, f"--ignore={FUNCTIONAL_TESTS_PATH} {opts}")


@task
def func_test(c, opts=""):
    """ Calls functional tests for python """
    run_pytest(c, f"{FUNCTIONAL_TESTS_PATH} {opts}")


@task
def test(c, opts=""):
    """ Runs functional and unit tests """
    run_pytest(c, f". {opts}")


@task
def populate_db(c):
    """ Calls the management commands to populate the db """
    _populate_db(c)


@task
def runserver(c):
    """ Runs the development server """
    _populate_db(c)
    with c.cd(ROOT_DIR):
        c.run(f"python manage.py runserver_plus --print-sql", pty=True)


@task
def migrate(c):
    """ Runs migrations """
    with c.cd(ROOT_DIR):
        c.run(f"python manage.py migrate", pty=True)
