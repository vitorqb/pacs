from invoke import task


FUNCTIONAL_TESTS_PATH = "functional_tests.py"


@task
def unit_test(c, opts=""):
    """ Calls pytest for all unit tests. """
    c.run(f"pytest --ignore={FUNCTIONAL_TESTS_PATH} {opts}", pty=True)


@task
def func_test(c, opts=""):
    """ Calls functional tests for python """
    c.run(f"pytest {FUNCTIONAL_TESTS_PATH} {opts}", pty=True)


@task
def test(c, opts=""):
    """ Runs functional and unit tests """
    c.run(f"pytest . {opts}", pty=True)
