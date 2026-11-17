# Shared Azure demonstration

The shared demo reuses the group's existing Ubuntu 24.04 VM in Sweden Central.
It runs the same FastAPI application and a **dedicated PostgreSQL container**, with
Caddy in front for public HTTPS. This does not reuse or modify another database
that might already be installed on the VM. Inspect the host before first deployment.

## Deployment state

**2026-11-17:** the account-based release is deployed and externally verified.
Selected application revision: `0f1e9d82a2ee36f687292b3781dd7778b6283364`.
Later documentation-only commits do not change the installed application revision.
The actual shared system uses the existing Ubuntu 24.04 VM in Sweden Central,
2 vCPU / 4 GiB, stable Compose project `aeris-shared`, persistent PostgreSQL volume
`aeris-shared_demo-data` and existing Caddy certificate volumes. Only Caddy ports 80/443
are public; app 8765 is loopback and PostgreSQL 5432 is not host-published. SSH is
restricted to approved source addresses. The selected source commit is returned
by `/health` and recorded in the release manifest and `RELEASE_COMMIT`.

Open [the shared dashboard](https://aeris-studiegruppe-linux.swedencentral.cloudapp.azure.com/)
when the VM is deliberately started. It now requires an individual account;
the previous shared token cannot authenticate. Johan is Admin; Esben, Nix and
Bilal are Technician. Credentials are handed over privately and each person
chooses a personal password. No repository/SSH/database credential is shared.

The exact CI-tested image and matching source archive were transferred with
verified checksums, loaded without rebuilding and promoted with a recent actual
isolated backup restore. Forward migration 002 preserved all existing domain data.
External HTTPS Postman passed 27 requests / 46 assertions. Account controls, all four
original complete cases and a new complete case were verified; the cases remained
identical after a real app/database restart. See [detailed evidence](verification-2026-11-17.md).

The VM's saved auto-shutdown is 00:00 Copenhagen time, with no automatic startup.
Manual deallocation/startup has been observed; the midnight job itself has not been
observed firing. This intentionally stopped demo is not continuous availability.
It is stopped/deallocated again after the authorized checks; start it for group
practice or the recording. Another member's own computer and examiner repo access
remain explicit human acceptance tasks.

The original November 6-7 pilot established trusted HTTPS, authenticated remote
access and data persistence using the earlier token-based release. Those historical
results do not establish the new account controls; the November 17 checks above do.
The host uses Docker Engine 29.9.3 and Compose 5.7.0. No paid monitoring stack,
additional VM or identity service was provisioned. Optional SigNoz remains local.

## One-time host preparation

1. Use an authorized personal SSH account and verify the host fingerprint. Never
   copy a private key to the VM/repository or disable SSH host-key verification.
   A network timeout differs from `Permission denied (publickey)`: the latter needs
   the correct username/key registration, not a wider firewall rule.
2. Inspect existing containers, listeners on 80/443/8765, available disk/RAM, and
   any existing database before installing anything. Preserve other group services.
   This small VM has 2 vCPUs and 4 GiB RAM; no additional paid cloud service is needed.
3. Install Docker Engine and its Compose plugin using [Docker's official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
   Do not blindly uninstall conflicting packages used by another project. Running
   Docker requires appropriate host privileges; Docker-group membership is root-equivalent.
4. Give the VM's **existing static public IP** an available Azure DNS label. Use its
   complete `swedencentral.cloudapp.azure.com` name below. DNS must resolve to the VM.
   Only TCP 80/443 are public for this app; SSH remains restricted to approved IPs.
   Do not open PostgreSQL, Docker, the app's internal port or the Caddy admin endpoint.
5. Keep releases under a dedicated directory owned by the deployment account, with
   a separate private settings file, for example `~/aeris/.env.shared`. In a release:

   ```sh
   python3 scripts/setup_shared.py YOUR-CONFIGURED-DNS-NAME --env-file ../../.env.shared
   ```

   Replace the DNS name first. The script refuses IP addresses, creates random
   credentials with owner-only permissions and **refuses to overwrite existing
   settings**. Reuse this file on later releases: changing POSTGRES_PASSWORD in a
   file does not rotate a PostgreSQL password in an existing volume. Never print
   the whole environment, run verbose shell tracing, or paste secrets into a PR.

## Release procedure

Follow [tested image delivery and recovery](release.md). The normal workflow is
feature -> dev -> main through PRs and checks. Select the approved immutable main
commit and its successful application run. The trusted publication job publishes
the same tested image to private GHCR; the source/image artifact also allows
promotion without storing a permanent registry credential on the VM.

1. Download the selected run's artifact; verify its GitHub digest, manifest revision
   and archive checksums. Transfer only the release bundle, not local credentials.
2. Take a private `pg_dump`, restore into a generated disposable database, compare
   complete domain/account fingerprints and remove only that disposable database.
3. Use the current `scripts/promote_release.py` from the reviewed maintenance tools
   with the exact revision, bundle, private settings, verified backup and releases
   directory. It preserves the stable project, database/certificate volumes and
   existing account data. Release roots are resolved before changing directory.
4. Verify `/health`, the authoritative `~/aeris/current` pointer, running image,
   external HTTPS, account controls and saved domain data. A log saying promotion
   succeeded alone is insufficient; the November 17 pointer regression illustrates why.

The old `scripts/deploy_shared.py` builds from source and remains useful for initial
setup; it is not the selected path for promoting the CI-tested image. Do not rebuild
an image on the VM and describe it as the same artifact CI tested. Do not use
`down --volumes`, volume pruning or a reset on the shared demonstration. Application
rollback does not undo a migration or authorize restoring token-only access.

For read-only host commands use the selected release's same private settings,
stable project and explicit Compose files. The app image override needs the
`AERIS_RELEASE_IMAGE` from its manifest; `docker exec` can inspect the named running
container without reinterpreting incomplete Compose configuration. Never print
settings, session/token tables, private credentials or shell tracing in a demo.

## Verify and hand over

1. From outside the VM, open the configured HTTPS URL with a normally trusted
   certificate. The new release shows individual sign-in; anonymous `/api/overview`
   must return HTTP 401. No browser-warning bypass is acceptable.
2. Bootstrap the initial Admin through the privileged host-side procedure in the
   [account guide](authentication.md). The Admin chooses a personal password and
   creates individual Technician accounts. Never share database/SSH credentials.
   The old API_TOKEN setting is ignored by the new release and must not be used.
3. To check a deliberately running shared release, use a private, mode-0600 JSON
   file bound to the exact HTTPS hostname with a Technician account, as described
   in `scripts/api_client.py` and the account guide. Then run:

   ```sh
   SMOKE_BASE_URL=https://YOUR-CONFIGURED-DNS-NAME SMOKE_EXPECT_SHARED=true SMOKE_CREDENTIALS_FILE=/private/path/to/accounts.json python3 scripts/smoke_test.py
   ```

   Passwords never belong in command arguments, URLs, issues or screenshots. TLS
   verification stays enabled. On macOS, if needed use the system CA bundle through
   `SSL_CERT_FILE=/etc/ssl/cert.pem`. This checks actual HTTPS/cookie login, data,
   Technician admin denial and logout; an in-process test is not external evidence.
4. Review a synthetic scenario, create a case, record a clearly simulated outcome
   and reload. Restart containers and verify the same records remain. Have another
   group member call the API from their own computer and record that evidence.
5. Verify Azure Auto-shutdown is On at 12:00 AM with the Copenhagen time zone.
   Midnight shutdown makes the dashboard unavailable; start the VM manually in
   Azure before a daytime session. A saved schedule is not evidence it has fired.

CI validates the Caddy configuration and shared-mode API authentication in an
isolated local Compose deployment, in addition to the application tests. It does
not hold cloud/SSH credentials or deploy arbitrary PRs. Shared release is an explicit
manual promotion of tested source; unattended Azure deployment is not implemented.

## Sources and rationale

- [Azure public IP and DNS labels](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/public-ip-addresses): reuse the existing public IP rather than another service.
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https) and [reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy): a small maintained TLS boundary, persistent certificates, public DNS/ports required.
- [Azure VM auto-shutdown](https://learn.microsoft.com/en-us/azure/virtual-machines/auto-shutdown-vm): scheduled stop with an explicit local time zone.
- [Course requirements](course-context.md): separate database, remote REST request, pipeline code and reproducible deployment. This proxy/token/DNS arrangement is a team implementation choice, not a prescribed course architecture.
