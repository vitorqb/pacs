from fabric import task
import os

# Load the .env
from dotenv import load_dotenv
load_dotenv('.env', verbose=True)


# Global variables
source_folder = f"/home/pacs/source/"


@task
def pre_deploy(c):
    """ Prepares the server for a deployment. MUST BE RUN AS ROOT.
    1 - Install all dependencies.
    2 - Ensures a pacs user exists, creating if needed.
    3 - Uploads the .env file. """
    _install_server_deps(c)
    _create_pacs_user(c)
    _upload_env_file(c)


@task
def deploy(c):
    """ Deploys the source code and prepares the database.
    Should be run as user `pacs`. Depends on environmental
    variables PACS_REPO_URL and """
    repo_url = os.environ['PACS_REPO_URL']
    commit = os.environ['PACS_COMMIT']
    site_folder = f"/home/pacs/site/"
    venv_folder = f"/home/pacs/venv/"

    _create_directories(c, [site_folder, source_folder])
    _git_clone(c, repo_url, commit)
    _prepare_virtualenv(c, venv_folder)
    c.put('.env', f'{source_folder}.env')
    _prepare_static_files(c, venv_folder)
    _update_db(c, venv_folder)


@task
def post_deploy(c):
    _setup_nginx(c)
    _setup_gunicorn(c)
    c.run("reboot")


def _install_server_deps(c):
    """ Install all dependencies from apt-get """
    apt_get_cmd = "apt-get --no-upgrade --assume-yes"
    deps = 'nginx python3.6 python-virtualenv make'
    c.run(f"{apt_get_cmd} update")
    c.run(f'{apt_get_cmd} install {deps}')


def _create_pacs_user(c):
    """ Creates a "pacs" user if it does not exist, and adds the
    current user public key to its allowed keys """
    def _pacs_user_exists(c):
        return c.run('id -u pacs', hide=True, warn=True)

    if not _pacs_user_exists(c):
        c.run('adduser --disabled-password --gecos "" pacs')
        _add_pub_key_to_allowed_keys(c)


def _upload_env_file(c):
    """ Uploades the file with environmental variables .env to the
    pacs user home folder """
    c.put(".env", "/home/pacs/.env")


def _add_pub_key_to_allowed_keys(c):
    """ Copies the key in /.ssh/id_rsa.pub to the allowed_keys file of
    the newly created pacs user in the server. """
    pub_key_file = os.path.expanduser("~/.ssh/id_rsa.pub")
    remote_authorized_keys_file = "/home/pacs/.ssh/authorized_keys"
    tmpfile_in_remote = "/home/pacs/tmp_pub_key"
    c.put(pub_key_file, tmpfile_in_remote)
    c.run(f"mkdir -p /home/pacs/.ssh")
    c.run(f"touch {remote_authorized_keys_file}")
    c.run(f"cat {tmpfile_in_remote} >> {remote_authorized_keys_file}")
    c.run(f"rm {tmpfile_in_remote}")
    c.run(f"chown -R pacs /home/pacs/.ssh")


def _create_directories(c, dirs):
    for d in dirs:
        c.run(f"mkdir -p {d}")


def _git_clone(c, repo_url, commit):
    """ Clones the repo in repo_url into source_folder (fresh) and
    checks out to a specific commit. """
    c.run(f"rm -fr {source_folder} && git clone {repo_url} {source_folder}")
    with c.cd(f"{source_folder}"):
        c.run(f"git checkout {commit}")


def _prepare_virtualenv(c, venv_folder):
    """ Creates a new fresh virtualenv and install all dependencies in it """
    c.run(f"rm -fr {venv_folder} && virtualenv -p /usr/bin/python3.6 {venv_folder}")
    with c.prefix(f"cd {source_folder} && source {venv_folder}bin/activate"):
        c.run(f"make requirements")


def _prepare_static_files(c, venv_folder):
    with c.prefix(f"cd {source_folder} && source {venv_folder}bin/activate"):
        c.run("python manage.py collectstatic --no-input")


def _update_db(c, venv_folder):
    with c.prefix(f"cd {source_folder} && source {venv_folder}bin/activate"):
        c.run("python manage.py migrate --no-input")
        c.run("python manage.py populate_accounts")
        c.run("python manage.py populate_currencies")


def _setup_nginx(c):
    """ Prepares the nginx config file using the template and variables in
    .env, and copies sets nginx to use them """
    sites_available_folder = "/home/pacs/sites_avaiable"
    sites_available_file = f"{sites_available_folder}/pacs"
    sites_enabled_file = f"/etc/nginx/sites-enabled/pacs"
    nginx_template_file = f"{source_folder}/deploy_tools/nginx.template.config"

    c.run(f"rm -rf {sites_available_folder} && mkdir -p {sites_available_folder}")
    # reads the .env file and exports all variables
    with c.prefix("export $(grep -v '^#' /home/pacs/.env | xargs -0)"):
        c.run(f" envsubst '$PACS_STATIC_ROOT:$PACS_GUINCORN_SOCKET'"
              f" <{nginx_template_file} >{sites_available_file}")
    c.run(f"rm -f {sites_enabled_file} &&"
          f" ln -s {sites_available_file} {sites_enabled_file}")
    c.run(f"systemctl reload nginx || systemctl start nginx")
    c.run(f"nginx -t")


def _setup_gunicorn(c):
    """ Prepares the gunicorn using the template file and variables
    in .env. """
    template_file = f"{source_folder}/deploy_tools/gunicorn-pacs.template.service"
    systemd_file = f"/etc/systemd/system/gunicorn-pacs.service"

    # With the .env variables exported...
    with c.prefix(f"export $(grep -v '^#' /home/pacs/.env | xargs -0)"):
        c.run(f" envsubst <{template_file} >{systemd_file}")
    c.run(f"systemctl enable gunicorn-pacs")
    c.run(f"systemctl stop gunicorn-pacs || :")
    c.run(f"systemctl start gunicorn-pacs || :")
