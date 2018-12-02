## Deploying to a (new) server

This assumes you are deploying to a Ubuntu 18.04 x64. The commands are intended
to be idempotent.

### Setting up
You will need to add a `.env` on this dir file with **all entries from the .env**
**file from the project root** plus some other variables:
```
PACS_GUINICORN_SOCKET=... # Where to put the guinicorn socket
```
These variables in the `.env` file will be used on the server.

Furthermore, other env variables must be set locally at the time of execution
of the script:
```
PACS_COMMIT=... # The commit (or branch name) used for the deploy.
PACS_REPO_URL=... # the url to the repo (for git clone)
```

### Deploying
Simply run the command:
```bash
export PACS_COMMIT=... PACS_REPO_URL=... && fab -H root@{{host}} deploy
```
