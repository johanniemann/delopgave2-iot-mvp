# Shared Azure demonstration

The shared demo reuses the group's existing Ubuntu 24.04 VM in Sweden Central.
It runs the same FastAPI application and a **dedicated PostgreSQL container**, with
Caddy in front for public HTTPS. This does not reuse or modify another database
that might already be installed on the VM. Inspect the host before first deployment.

## Deployment state

**2026-11-08 account release:** this branch replaces the shared token with individual
Admin/Technician sessions. It is verified locally and has not been promoted to Azure.
The installed VM release described below still uses the earlier token arrangement.
Read [account bootstrap, forward migration and recovery](authentication.md) before
promoting; do not apply the new release without preparing the first administrator.


The accepted prototype is running on the existing VM. The approved Azure firewall
permits TCP 80/443 and restricts Johan's
SSH rule to his current public IPv4 /32. The VM's nightly shutdown is enabled at
**00:00 in the Copenhagen time zone**. There is no automatic startup schedule.
The existing static public IP now has the verified DNS name
`aeris-studiegruppe-linux.swedencentral.cloudapp.azure.com` (20.91.193.131).

Open [the shared dashboard](https://aeris-studiegruppe-linux.swedencentral.cloudapp.azure.com/)
with the group's private access token. The 2026-11-06 pilot verified personal SSH
access, a fresh Docker installation, HTTP-to-HTTPS redirect, a publicly trusted
certificate, real PostgreSQL readiness, HTTP 401 without a token, and authenticated
API calls from the developer's Mac to the VM. The public browser walkthrough saved
a review and case; a failed simulated outcome kept it open, and a successful one
resolved it. Synthetic QA records are labelled accordingly. This is an external
computer calling the VM API; it is not evidence that every teammate has tested access.

The actual app and database containers were stopped and started with the same named
volume. The full QA case response (96 readings, saved review, two outcomes and event
history) was identical before/after. Local validation passed 43 application tests,
11 helper/guidance tests, repository/whitespace checks, Caddy validation, and real
local/shared HTTP smoke checks. [PR #4](https://github.com/johanniemann/delopgave2-iot-mvp/pull/4)
was merged on 2026-11-07 after all five checks passed and the owner explicitly
authorized an exception while the other members were unavailable. This was an owner
merge decision, not an independent review or self-approval. Teammate review remains
follow-up work. The VM's release directory records its source
commit in `RELEASE_COMMIT`, and `~/aeris/current` identifies the selected release.

The initial host inspection found no Docker/database packages or listeners on the
application/web/database ports. Docker Engine 29.9.3 and Compose plugin 5.7.0 were
installed from Docker's official signed Ubuntu repository. The app, database and
proxy have separate containers; only 80/443 are public, app 8765 is loopback only.
Shutdown is saved in Azure; an actual midnight stop has not yet been observed.

On 2026-11-07 the VM was started from its previously verified deallocated state.
The named HTTPS endpoint, unauthenticated rejection, authenticated API and public
dashboard worked without reinstalling. The complete saved QA case response matched
the previous day's baseline, including 96 readings, the review, both outcomes and
events. The VM was then stopped and **Stopped (deallocated)** was verified again.
The automatic midnight schedule remains a separate saved safeguard; these manual
stops do not establish that the scheduled job itself has fired.

The owner selected the existing VM hostname after reviewing GitHub Pages. Pages
cannot directly host the Python/PostgreSQL service or turn a github.io address into
an arbitrary VM DNS alias. It also needs a qualifying plan for a private source
repository. No public frontend repository, Pages site, domain purchase or subscription
was created. The selected topology remains one origin for dashboard and API.

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

Use a reviewed commit with passing application/repository checks. The initial
authorized pilot may use the deployment task branch; record that explicitly rather
than claiming it is merged or independently reviewed. Keep the source commit ID
with the release. Transfer only versioned source (for example a `git archive`), not
the developer's `.env`, local database, SSH keys or full school folder. The VM does
not need a permanent GitHub token or write access to the repository.

From the chosen release directory **on the VM**, with Docker access:

```sh
python3 scripts/deploy_shared.py --env-file ../../.env.shared
```

The current Azure account uses `sudo -n python3 scripts/deploy_shared.py --env-file
../../.env.shared` instead of Docker-group membership. It already has authorized
administrator access; the release procedure does not grant another account access.

The script checks private file permissions, validates the merged configuration and
Caddyfile, then builds/starts the `aeris-shared` Compose project. Keep that project
name stable: its named PostgreSQL and certificate volumes survive container rebuilds
and VM shutdown/start. The app remains on loopback port 8765; Caddy reaches it over
the Compose network. Only Caddy publishes web ports. Caddy automatically redirects
HTTP to HTTPS and obtains/renews a trusted certificate when public DNS/80/443 work.
Its admin endpoint is not published. Container logs have bounded rotation.
Uvicorn does not trust forwarded client addresses; behind this single proxy the
existing 60-write/minute limit is shared by the demo group, not a per-person quota.

For host commands, always use the **same environment file, both Compose files and
project name**, substituting the real absolute path to the private settings:

```sh
docker compose --project-name aeris-shared --env-file ../../.env.shared -f compose.yaml -f compose.shared.yaml ps
```

The deployment script does not provision Azure, change firewall rules, delete
volumes or start the VM. The new app applies recorded forward migrations on startup. On a failed release, inspect status
and return to the previous compatible source release with the same settings/project.
Never use `down --volumes`, `docker system prune --volumes` or a database reset on
the shared demo. Before a schema change, make a private `pg_dump` backup and design
a forward migration; restoring old source cannot undo a database migration.

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
