# Usage:
# HOST=... PACS_COMMIT=... deploy_full.sh
fab -H root@$HOST pre-deploy && fab -H pacs@$HOST deploy && fab -H root@$HOST post-deploy
