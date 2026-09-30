# Backup, restore and update requirements

Automated encrypted export/restore and the restricted update companion are not
implemented. Do not rely on this development build for the approved RPO/RTO.

The target is daily encrypted backups retained for seven days, a 24-hour RPO and
one-hour lab restore. The future archive must include a schema/version manifest,
verified authenticated encryption, and an independently protected recovery key.
A database dump alone does not recover encrypted credentials without the root key.
Treat database copies and `.env` as secrets and never commit them to Git.

Restore must validate compatibility before changing state, support dry-run review,
and leave publishing/provisioning disabled until explicitly resumed. A separate
clean-host test is required. Configuration export and full historical database
backup are distinct operations.

Development updates: stop the control service, preserve data and secrets, review
migrations, rebuild the pinned source revision and start Compose. There is no
generic rollback guarantee. Production update acceptance requires tested backups,
active-session draining, compatible migration ordering, signed/digested images and
health verification. Never mount an unrestricted Docker socket into control.
