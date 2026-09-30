# Local development appliance installation

This installs the **configuration foundation**, not a working restreaming v1.
Public/cloud deployment is deliberately unavailable until authentication, media
execution and networking gates are complete.

## Docker Compose

On a Linux host with Docker and Compose:

```sh
git clone https://github.com/camarokris/TDRestreamer.git
cd TDRestreamer
python3 scripts/configure.py
docker compose --env-file .env -f deploy/compose/compose.yaml up -d --build
```

Open http://127.0.0.1:8080. Choose **First time? Set up this appliance**. Read
TDR_BOOTSTRAP_TOKEN from your local `.env` without posting it in support tickets.
Choose a username, a password of at least 12 bytes, and a workspace name.
The setup token stops working after the first user is created. Sign in locally.

The default stack contains PostgreSQL, a one-shot migration container, and the
control/UI service. No Redis or media listener is enabled. PostgreSQL has no host
port publication. Control binds to loopback by default. Do not expose this
pre-release stack publicly. A trusted-LAN test can explicitly set TDR_BIND to a
specific LAN address; the UI is still authenticated.

The `.env` generator refuses to overwrite an existing file and sets mode 0600.
Keep the root encryption key: losing it makes stored destination credentials
unrecoverable. Database passwords are initialized only on the first volume start;
changing `.env` alone does not rotate an existing PostgreSQL role password.

## Using the foundation

- OBS inputs: save distinct horizontal/vertical/master identities and retain the
  newly generated token once. Actual OBS publication is not connected yet.
- Destinations: save a complete RTMP/RTMPS URL including key; subsequent reads
  return only metadata and credential status.
- Sessions: create configurations, request test mode, stop, and inspect revisions.
  These actions manage desired state only; no live media is processed.
- Compatibility: explore manual H.264/AAC geometry and track selections. This is
  not a live input probe or platform-specific bitrate/GOP approval.
- API documentation: expand endpoint definitions or send read-only requests.

## Stop and removal

`docker compose --env-file .env -f deploy/compose/compose.yaml down` stops services
while retaining PostgreSQL data. Adding `-v` destroys appliance data; use it only
for disposable installs. Never delete the `.env` encryption key accidentally.
