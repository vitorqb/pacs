#!/bin/bash
# Tempalte for a bash script that set's up a daily megasync backup for
# pacs db file.
set -x


MEGACMD_PKG_URL='https://mega.nz/linux/MEGAsync/xUbuntu_18.04/amd64/megacmd-xUbuntu_18.04_amd64.deb'
BASE_FOLDER="/home/pacs/megasync-db-backup/"
BACKUP_SCRIPT="${BASE_FOLDER}run-backup.bash"
SYSTEMD_SERVICE_NAME="pacs-megasync-db-backup"


function create-base-folder() {
    mkdir -p "$BASE_FOLDER"
}

function maybe-install-megacmd() {
    # Skip if already installed
    if which mega-cmd >/dev/null
    then
        return 0
    fi

    # install megacmd
    local dest="${BASE_FOLDER}megacmd-installation"
    mkdir -p "$dest"
    curl "$MEGACMD_PKG_URL" -o "$dest/megacmd.deb"
    apt --assume-yes install "$dest/megacmd.deb"
    rm -rfv $dest
}

function cat-systemd-timer-file-for-backup() {
    cat <<EOF
[Unit]
Description=Run megasync backup for pacs db daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=multi-user.target
EOF
}

function cat-systemd-service-file-for-backup() {
    cat <<EOF
[Unit]
Description=Megasync backup for pacs db

[Service]
User=pacs
WorkingDirectory=/home/pacs/
EnvironmentFile=/home/pacs/.env
ExecStart=${BACKUP_SCRIPT}
EOF
}

function cat-backup-bash-script() {
    cat <<EOF
#!/bin/bash
mega-logout -vv
mega-login -vv \${MEGA_USER} \${MEGA_PASSWORD}
rm -rfv ${BASE_FOLDER}db-backups && mkdir -p ${BASE_FOLDER}db-backups
tar -vzcf ${BASE_FOLDER}db-backups/\`date +%Y%m%d%H%M%S\`.tar.gz \${PACS_DB_FILE}
mega-put -vv -c ${BASE_FOLDER}db-backups/* \${MEGA_REMOTE_BACKUP_FOLDER}
mega-logout -vv
EOF
}

function enable-systemd-timer-for-backup() {
    systemctl enable "$SYSTEMD_SERVICE_NAME".timer
    systemctl restart "$SYSTEMD_SERVICE_NAME".timer
}


[ ! -z "$DRYRUN" ] && return

create-base-folder\
    && maybe-install-megacmd\
    && cat-systemd-service-file-for-backup >/etc/systemd/system/"$SYSTEMD_SERVICE_NAME".service\
    && cat-systemd-timer-file-for-backup >/etc/systemd/system/"$SYSTEMD_SERVICE_NAME".timer\
    && cat-backup-bash-script >"${BACKUP_SCRIPT}"\
    && chmod +x "${BACKUP_SCRIPT}" \
    && enable-systemd-timer-for-backup \
    && chown -R pacs "${BASE_FOLDER}"
