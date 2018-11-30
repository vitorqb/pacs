from fabric import task
import os

# Load the .env
from dotenv import load_dotenv
load_dotenv('.env', verbose=True)


REPO_URL = os.environ['PACS_REPO_URL']
COMMIT = os.environ['PACS_COMMIT']


@task
def prepare_server(c):
    _install_server_deps(c)
    _create_pacs_user(c)


def _install_server_deps(c):
    c.run('apt-get update')
    deps = ['nginx', 'python3.6', 'python-virtualenv', 'make']
    c.run(f'apt-get --no-upgrade --assume-yes install {" ".join(deps)}')


def _create_pacs_user(c):
    # Creates a pacs user if it does not exists, and copies the
    # ssh keys there
    if not c.run('id -u pacs', hide=True, warn=True):
        c.run('adduser --disabled-password --gecos "" pacs')
        _add_pub_key_to_allowed_keys(c)


def _add_pub_key_to_allowed_keys(c):
    pub_key_file = os.path.expanduser("~/.ssh/id_rsa.pub")
    remote_authorized_keys_file = "/home/pacs/.ssh/authorized_keys"
    tmpfile_in_remote = "/home/pacs/tmp12829790010293"
    c.put(pub_key_file, tmpfile_in_remote)
    c.run(f"mkdir /home/pacs/.ssh")
    c.run(f"touch {remote_authorized_keys_file}")
    c.run(f"cat {tmpfile_in_remote} >> {remote_authorized_keys_file}")
    c.run(f"rm {tmpfile_in_remote}")
    c.run(f"chown -R pacs /home/pacs/.ssh")


@task
def deploy(c):
    site_folder = f"/home/pacs/site/"
    source_folder = f"/home/pacs/source/"
    venv_folder = f"/home/pacs/venv/"

    _create_directories(c, [site_folder, source_folder])
    _git_clone(c, source_folder)
    _prepare_virtualenv(c, venv_folder, source_folder)
    c.put('.env', f'{source_folder}.env')
    _prepare_static_files(c, source_folder, venv_folder)


def _create_directories(c, dirs):
    for d in dirs:
        c.run(f"mkdir -p {d}")


def _git_clone(c, source_folder):
    c.run(f"rm -fr {source_folder}")
    c.run(f"git clone {REPO_URL} {source_folder}")
    with c.cd(f"{source_folder}"):
        c.run(f"git checkout {COMMIT}")


def _prepare_virtualenv(c, venv_folder, source_folder):
    c.run(f"rm -fr {venv_folder}")
    c.run(f"virtualenv -p /usr/bin/python3.6 {venv_folder}")
    with c.prefix(f"cd {source_folder} && source {venv_folder}bin/activate"):
        c.run(f"make requirements")


def _prepare_static_files(c, source_folder, venv_folder):
    with c.prefix(f"cd {source_folder} && source {venv_folder}bin/activate"):
        c.run("python manage.py collectstatic --no-input")
