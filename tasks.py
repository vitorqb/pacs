from invoke import task
import os


FUNCTIONAL_TESTS_PATH = "functional_tests.py"
ROOTDIT = os.path.abspath(os.path.dirname(__file__))


def run_pytest(c, opts):
    c.run(f"pytest {opts} --cov=.", pty=True)


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
def runserver(c):
    """ Runs the development server """
    with c.cd(ROOTDIT):
        c.run(f"python manage.py runserver_plus --print-sql", pty=True)
