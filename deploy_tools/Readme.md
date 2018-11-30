## Deploying to a new server

This assumes you are deploying to a fresh new Ubuntu 18.04 x64.

You will need to add a `.env` on this dir file with the following:
```
PACS_REPO_URL=... # the url to the repo (for git clone)
PACS_ALLOWED_HOSTS=... # A list of allowed hosts
PACS_SECRET_KEY=... # A secret key
PACS_STATIC_ROOT=... # STATIC_ROOT for django.
PACS_GUINICORN_SOCKET=... # Where to put the guinicorn socket
```

If it is the first deploy, run (as root):
```
fab -H root@{{host}} prepare_server
```

This install the dependencies and creates an user named pacs for you.


This creates a user named pacs for you. Then:
``` bash
PACS_COMMIT=... fab -H pacs@{{host}} deploy
# Where PACS_COMMIT is the commit to deploy (or anything you can git checkout into).
```

In a single command, if you want to
```bash
export PACS_COMMIT=... & fab -H root@{{host}} prepare_server & fab -H pacs@{{host}} deploy
```
