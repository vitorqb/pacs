# Personal Account System (pacs)

A small personal project for a system to keep track of my personal finances.

This repo contains the REST API web server (written in python-django).

A web frontend in react is available at https://github.com/vitorqb/pacs-react.

## Setting up

Make sure you have https://github.com/pyinvoke/invoke installed and

```
cd <path/to/git/clone>
cp .env.example .env
inv prepare-virtualenv ./venv && . venv/bin/activate
inv migrate runserver
```

## Running tests

```
. venv/bin/activate && inv test
```

### Configuration variables

The system configuration depends on environmental variables. Those can
be set by the user or in a `.env` file at the project root (here).

Those variables are:
```bash
PACS_DEBUG=1  # If set to 1, enters in debug mode. Any other values leads to production mode
PACS_SECRET_KEY=... # SECRET_KEY in django settings
PACS_ALLOWED_HOSTS=... # comma separated ALLOWED_HOSTS for django settings
                       # e.g. 128.6.2.1,www.google.com
PACS_STATIC_ROOT=... # STATIC_ROOT for django settings.
PACS_DB_FILE=... # The path to the db file (can be relative to cur dir)
PACS_ADMIN_TOKEN=... # Token used to login as admin
PACS_LOG_FILE=... # Where to send logs. May have ~.
```

See .env.example for an example.

## Usefull commands

### Connecting to the db

```sh
ssh -t "root@${PACS_HOST}" "sqlite3" "/pacs_db.sqlite3"
```
