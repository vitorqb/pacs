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
    c.put(".env", "/home/pacs/.env")


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
    _update_db(c, source_folder, venv_folder)


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


def _update_db(c, source_folder, venv_folder):
    with c.prefix(f"cd {source_folder} && source {venv_folder}bin/activate"):
        c.run("python manage.py migrate --no-input")
        c.run("python manage.py populate_accounts")
        c.run("python manage.py populate_currencies")


@task
def post_deploy(c):
    _setup_nginx(c)
    _setup_gunicorn(c)
    c.run("reboot")


def _setup_nginx(c):
    sites_available_folder = "/home/pacs/sites_avaiable"
    sites_available_file = f"{sites_available_folder}/pacs"
    sites_enabled_file = f"/etc/nginx/sites-enabled/pacs"
    tmp_file = "/home/pacs/tmp_nginx"

    # Set up
    c.run(f"rm -rf {sites_available_folder} && mkdir -p {sites_available_folder}")
    c.put("nginx.template.config", tmp_file)

    # Action
    c.run("export $(grep -v '^#' /home/pacs/.env | xargs -0) &&"
          " envsubst '$PACS_STATIC_ROOT:$PACS_GUINCORN_SOCKET'"
          f" < {tmp_file}"
          f" > {sites_available_file}")
    c.run(f"cat {sites_available_file}")
    c.run(f"rm -f {sites_enabled_file} &&"
          f" ln -s {sites_available_file} {sites_enabled_file}")
    c.run(f"systemctl reload nginx || systemctl start nginx")
    c.run(f"nginx -t")

    # Tear down
    c.run(f"rm {tmp_file}")


def _setup_gunicorn(c):
    tmp_file = "/home/pacs/tmp_gunicorn"
    systemd_file = "/etc/systemd/system/gunicorn-pacs.service"

    c.put(f"./gunicorn-pacs.template.service", tmp_file)
    c.run(f"export $(grep -v '^#' /home/pacs/.env | xargs -0) &&"
          f" envsubst <{tmp_file} >{systemd_file}")
    c.run(f"cat {systemd_file}")
    c.run(f"systemctl enable gunicorn-pacs")
    c.run(f"systemctl stop gunicorn-pacs || :")
    c.run(f"systemctl start gunicorn-pacs || :")
