## Deploying to a (new) server

This assumes you are deploying to a Ubuntu 18.04 x64. The commands are intended
to be idempotent.

### Setting up
You will need to add a `.env` on this dir file with the following:
```
PACS_ALLOWED_HOSTS=... # A list of allowed hosts
PACS_SECRET_KEY=... # A secret key
PACS_STATIC_ROOT=... # STATIC_ROOT for django.
PACS_GUINICORN_SOCKET=... # Where to put the guinicorn socket
```
These variables in the .env file are used on the server.

Furthermore, these env variables must be set locally at the time of execution
of the script:
```
PACS_COMMIT=... # The commit (or branch name) used for the deploy.
PACS_REPO_URL=... # the url to the repo (for git clone)
```

### Deploying
The deploy has three stages:

1) Prepare the server, which must be run as root. Check `fab pre-deploy --help` for info.
```
# AS ROOT!
fab -H root@{{host}} prepare-server
```

2) Deploy. Must be run as `pacs`, a user created in 1). Refer to `fab deploy --help`.
``` bash
PACS_COMMIT=... fab -H pacs@{{host}} deploy
# Where PACS_COMMIT is the commit to deploy (or anything you can git checkout into).
```

3) Prepare server services (nginx, gunicorn) to use the new deploy. Must be ran as root.
    Refer to `fab post-deploy --help`.
```bash
fab -H root@{{host}} post-deploy
```


In a single command:
```bash
export PACS_COMMIT=... && export HOST=... && fab -H root@$HOST pre-deploy && fab -H pacs@$HOST deploy && fab -H root@$HOST post-deploy
```
