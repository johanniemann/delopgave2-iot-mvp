# Tested releases, backup and recovery

## Build once and promote explicitly

The team uses feature -> dev -> main. Application checks first require the locked
Bandit/dependency gate and repository/helper checks, then run real PostgreSQL tests,
build the runtime image, start it, exercise HTTP/Newman and verify a real database
backup/restore. No cloud credentials are supplied to PR jobs.

The last externally verified shared release is
`0f1e9d82a2ee36f687292b3781dd7778b6283364`. The later quality-improvement candidate
adds stricter archive verification and proxy client identity; a source change alone
does not install it. Keep [deployment status](deployment.md) tied to the revision
actually observed on the VM.

Successful push/manual runs package that exact running image plus `git archive`
of the same source commit. `release.json` records the commit, platform, image ID
and archive checksums. The private Actions artifact lasts one day. Pushes to dev
or main also publish the **same image, without rebuilding**, to the repository's
GHCR package with `sha-COMMIT` tags. Only that separate trusted job gets temporary
package-write permission. Package visibility must remain private.

The artifact is a short-lived transfer option when the host should not retain a
registry credential. Download it using authorized repository access and transfer
the three package files over the existing verified SSH connection. Never transfer
the developer's environment/account files. A checksum protects transfer integrity;
it is not an independent signature or a substitute for reviewing the selected commit.

`GET /health` includes the commit embedded in the runtime image. Use it to check
which release actually runs; merge and deployment remain different operations.

## Private backup and actual restore

Select the environment explicitly. For a local project:

```sh
python3 scripts/database_backup.py backup-and-verify --project aeris-prototype
```

On the existing shared host, from a release containing this helper:

```sh
sudo -n python3 scripts/database_backup.py backup-and-verify \
  --project aeris-shared --shared --env-file ../../.env.shared \
  --directory ../../backups
```

Keep backups off Git and protect their directory with mode 0700 and files with
0600. Dumps include account/session information and are private even though turbine
measurements are synthetic. Keep an additional private copy outside the VM before
removing disks or resources. A backup on the same disk alone is not disaster recovery.

The helper compares source domain/account evidence before and after pg_dump and
refuses to certify a backup taken during a concurrent data change. Use a quiet
window and retry when necessary. It restores the dump into a newly generated
`aeris_restore_*_test` database, checks every saved table's canonical content,
then drops only that generated test database. Transient sessions/login throttles
are restored but excluded from the content comparison because ordinary HTTP reads
may refresh sessions. A `.verified.json` file is written only after success.
The current helper includes the verified archive's basename and SHA-256 in that
file. Keep the dump and verification file in the same private directory. Promotion
requires that exact adjacent dump to remain a private regular file, rejects
symlinks, and rechecks its checksum as well as the restore's age. An old verification
file without the archive basename cannot authorize promotion: create and verify a
fresh backup using the current tools; do not manually add fields to old evidence.

The [data-handling policy](data-handling.md) covers the account and session material
inside private dumps and the manual review of retained copies at project closure.

Both a v1 source and a later account schema are supported: table names come from
the selected schema and are restricted before composing queries. No restore is
ever directed at the live `aeris` database by this verification command.

## Shared image promotion

Use Python 3.12+ on the existing Ubuntu host. Select an approved full commit and
its successful CI run. Confirm the package revision and platform, a verified
backup from the last 24 hours with its intact adjacent private dump, stable settings
and Compose project `aeris-shared`.

From a trusted copy of the release tools on that host:

```sh
sudo -n python3 scripts/promote_release.py \
  --bundle ../../incoming/SELECTED-BUNDLE \
  --revision FULL-APPROVED-40-CHARACTER-COMMIT \
  --env-file ../../.env.shared \
  --backup-verification ../../backups/SELECTED.verified.json \
  --releases ../../releases
```

The helper checks archives before extraction, rejects links/path traversal,
requires unchanged source evidence since the verified backup, loads the packaged
image and verifies its ID/revision. It starts the selected image with `--no-build`
and `--pull never`, retaining the shared database and Caddy volumes. Startup runs
recorded forward migrations. After readiness it compares all pre-existing tables
(except the advancing schema-version table) and only then moves the `current`
symlink. Account bootstrap is a separate privileged step described in
[authentication](authentication.md). Never restore the old shared-token access
implicitly as part of recovery.

A failed promotion leaves its release directory for inspection and does not
automatically restore a database or downgrade schema. Inspect actual containers,
logs and compatibility before choosing an already verified application image.
Moving a symlink alone does not change the running containers. Full database
recovery requires a separately selected private backup and an explicit maintenance
decision; the test-restore helper deliberately cannot overwrite the live database.

After promotion, perform the external HTTPS/login/role/CSRF/logout checks and
compare saved cases/readings/events. Confirm the source commit via `/health`.
Only then record the release as verified in [deployment](deployment.md).

## Operational signals

For this MVP the default operational evidence is database readiness at `/health`,
bounded container logs, JSON security rejections, domain events and account-admin
history. Authenticated account UUIDs are retained only where useful; rejected
request input and secrets are not copied to the security log. Logs rotate in
shared mode. Retain only what the study-group demonstration needs.

The [optional local SigNoz demo](observability.md) remains separate and disabled
in shared mode. It can illustrate request counts, timings and a 503 alarm. The
default signals above can demonstrate failure/recovery without installing another
monitoring stack on the VM. A local or same-host monitor is not external uptime
coverage. Nightly intentional VM shutdown must not be described as continuous uptime.

## Verification state

Earlier baseline on 2026-11-17: real backup/restore comparison passed, as did the expanded
Postman workflow and 73 application tests. Helper safety checks reject altered
archives, path traversal, wrong-project evidence and unsafe restore targets.
Trusted GHCR publication, checksummed CI artifacts, actual shared promotion, external
HTTPS/Postman/account controls and persistence after an app/database restart were
verified on 2026-11-17. See [recorded evidence](verification-2026-11-17.md). A final
relative-path defect was reproduced and fixed with a full-entry-point regression;
all 24 helper tests passed for that baseline. Those historical counts do not prove
the later quality-improvement candidate. Record fresh helper/proxy/application
results before promoting it. Always verify both the runtime image and shared current
pointer, as well as data, after promotion.

Official references checked 2026-11-17:
[pip-audit](https://github.com/pypa/pip-audit),
[Bandit thresholds](https://bandit.readthedocs.io/en/latest/man/bandit.html),
[Actions artifacts](https://github.com/actions/upload-artifact), and
[GHCR authentication](https://github.com/docker/login-action).
