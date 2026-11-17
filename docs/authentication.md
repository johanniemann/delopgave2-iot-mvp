# Individual accounts and two roles

Selected team requirement, 2026-11-08: replace anonymous local access/shared bearer
access with individual accounts. No external identity service, signup or third role.

| Capability | Technician (Maintenance specialist) | Admin |
| --- | --- | --- |
| Read all turbine evidence, cases and activity | Yes | Yes |
| Create synthetic scenarios, review forecasts, create cases and record simulated outcomes | Yes | Yes |
| Change own password and sign out | Yes | Yes |
| List/create/edit/deactivate users, assign either role, reset passwords | No | Yes |
| Inspect account administration history | No | Yes |

This is one shared study-group workspace; technicians are not isolated by case.
Forecast reviewer identity comes from the authenticated account, never caller text.
Existing synthetic/seeded review evidence remains unchanged. Admin means application
administration; it grants no GitHub, Azure, Docker or SigNoz rights.

## HTTP contract

- `POST /api/auth/login`: username/password; sets an HttpOnly SameSite=Strict cookie,
  returns the public user, expiry and a CSRF token. Generic 401 for invalid/inactive
  accounts. Persistent per-account/per-peer throttling returns 429.
- `GET /api/auth/me`: current public user and CSRF token; 401 without a live session.
- `POST /api/auth/logout`: invalidate this session and clear cookie.
- `POST /api/auth/password`: current_password/new_password; revoke all sessions.
- `GET/POST /api/admin/users`: list/create accounts (admin only).
- `PATCH /api/admin/users/{uuid}`: display_name, role, active and expected_version.
- `POST /api/admin/users/{uuid}/password`: temporary password + expected_version;
  revoke sessions and require a password change on next login.
- `GET /api/admin/audit`: latest 100 administrative facts, without passwords/tokens.

All existing domain routes require either role. All authenticated writes also need
`X-CSRF-Token` from login/me. Auth and admin bodies reject unknown fields. New users
and reset passwords require a password change before domain/admin access. Passwords
are 15-128 characters and preserved exactly (including spaces), hashed with Argon2id.
Sessions have an 8-hour absolute and 30-minute idle expiry, are hashed in PostgreSQL,
rotate on login and are revoked on role/status/password changes. Shared mode uses
Secure host-only cookies over HTTPS. No shared bearer token bypass remains.

User changes serialize under a database lock, recheck the acting admin, check an
expected version and preserve at least one active admin. Accounts are deactivated
rather than deleted so evidence keeps its original identity. Self-demotion and
self-deactivation are refused. No email delivery or password-recovery service exists;
an administrator resets another user's temporary password. Host-side recovery is
an explicit privileged operation, not a public reset endpoint.

Migration 002 adds account/session/throttle/audit tables; it does not alter existing
case data. It must be applied forward before the new code serves authenticated data.
The authorized Azure forward migration was completed on 2026-11-17; existing case evidence was preserved. See [verified release evidence](verification-2026-11-17.md).

## Start locally

```sh
python3 scripts/setup_demo.py
docker compose up -d --build --wait app
python3 scripts/setup_accounts.py
```

Open `http://localhost:8765`. The last command creates two **local demo** accounts,
`admin` and `technician`, with independently generated random passwords. Credentials
are in ignored `.env.accounts-8765.json`, mode 0600, bound to this host/port. They are
not default/shared passwords and are never printed or committed. Existing settings,
accounts and case data are preserved. For the isolated SigNoz demo use
`python3 scripts/observability.py up`; it prepares `.env.accounts-8766.json` instead.
These two clearly local demo accounts can be tried immediately. Users subsequently
created/reset through Admin must change their temporary password before working.

Sign in as Admin → **User administration** → **Add user**. Set a unique username,
display name, one of the two roles and a temporary password; supply it privately.
**Edit** changes display name, role and active status. **Reset password** ends their
sessions and requires a new personal password. Click your own profile name to change
your password, or **Sign out** to end this browser's session. Role/status/name edits
also end the affected account's sessions. Initial host setup and later account
changes appear in administration history. Existing historical review names remain
unchanged; new reviews contain the authenticated name and stable account UUID.

Each member's local accounts/database are separate. Local Compose uses distinct
cookie names per published app port so the 8765/8766 demos do not overwrite each
other's browser session. Shared HTTPS uses the `__Host-aeris-session` cookie. On the shared deployment,
an administrator creates one real account per member. Do not share a local demo
credential file, copy passwords into Git or reuse an Azure/GitHub password here.

## Shared deployment and host recovery

The user authorized the shared promotion and specifically approved Johan/Admin,
Esben/Nix/Bilal/Technician and one temporary Technician test account. The shared
release was migrated on 2026-11-17 with a verified restore and the established
stable Compose project/volume. Before every later promotion take and verify a backup. Migration 002 adds only new tables and a recorded schema version;
a rollback of application code does not remove those tables or reactivate the old
shared token. Treat any rollback that restores token-only access as an explicit
access-policy change, not an automatic recovery action.

On the authorized host, create a private JSON file with `admin` containing username,
display_name and a fresh password. Pass that file on stdin to the running app:

```sh
docker compose --project-name aeris-shared --env-file /private/path/to/settings \
  -f compose.yaml -f compose.shared.yaml exec -T app \
  /app/.venv/bin/python -m app.accounts bootstrap < /private/path/to/initial-account.json
```

Bootstrap refuses if accounts already exist, creates only the initial Admin in
shared mode, and requires that person to choose their own password at first login.
It never exposes a public registration/setup endpoint. Protect/remove the temporary
credential file after handoff. The old API_TOKEN setting is ignored by this code.

For a forgotten sole-admin password, an authorized host operator can supply private
JSON with `username` and a new temporary `password` to the same command using
`recover-admin` instead of `bootstrap`. It operates only on an existing active Admin,
revokes sessions, requires a personal password change and records the recovery.
It cannot promote a Technician. There is no email reset, MFA or external identity
provider; these remain limits of this small prototype.

Login throttles are persistent: 10 attempts per username and 30 per network peer
per five minutes. Behind Caddy, peer limits may be shared by the whole group;
forwarded headers are not trusted to bypass the limit. Repeated retries can block
valid sign-ins temporarily. Session revocation applies on the next request; already
running work is not cancelled. The HTTP-only CI proxy check does not authenticate
with Secure cookies; HTTPS cookie behavior is separately covered by integration tests.

## Earlier verification on the local Mac — 2026-11-08

- **70 application tests passed** against real PostgreSQL: direct role denial,
  forced password change, CSRF, expiry, logout, revocation, resets, concurrent admin
  changes, last-admin protection, impersonation prevention and existing domain rules.
- **18 helper tests passed**, including credential target binding, private temporary
  Newman settings/cleanup and preservation of nonzero test exits.
- The actual HTTP smoke check passed anonymous rejection, Technician login/admin
  denial, saved evidence access and logout. Newman passed 17 requests/28 assertions.
  The updated authenticated failure helper also returned five expected 503 responses,
  restored the DB and verified HTTP 200 plus an unchanged complete saved case.
- Both Admin and Technician views were inspected in Brave. Admin's user list and
  creation form were visible; Technician had no administration menu. Actual account
  create/edit/reset/password-change behavior is covered by PostgreSQL HTTP tests;
  no fictitious human review is claimed.
- The already-populated local v1 database was upgraded, then its complete existing
  case JSON compared equal to the pre-upgrade baseline (all readings, review,
  outcomes and events). Repeated initialization also preserves evidence in tests.
- Actual SDK collection confirmed login password, cookie, CSRF token and query text
  are absent from exported traces/metrics. Private credential files are excluded
  from Git and Docker build context.

This is local Mac validation. These earlier results did not establish VM, another member's computer or Windows behaviour. It has no MFA, external identity service,
email recovery or distributed IP-aware edge limiter. These limits do not create a
third role or weaken API checks. Shared validation on 2026-11-17 is recorded below.

See [course context](course-context.md): E1/E2/E3 and C1/C2 support
access control, secret handling, safe failures and tests; two roles are a team choice.

Authoritative references checked 2026-11-08:
[OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
[session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
and [argon2-cffi](https://argon2-cffi.readthedocs.io/en/stable/howto.html).


## Shared verification — 2026-11-17

Actual external HTTPS calls verified the selected revision, valid certificate,
anonymous/old-bearer 401, temporary-password gate, Technician/admin 403, CSRF 403,
logout 401, session revocation after an account edit, and temporary-password reset.
All four pre-existing complete case responses matched their v1 baseline. The full
27-request / 46-assertion Postman workflow passed against the VM, and an actual
app/database restart preserved the original cases and the new complete case.

The temporary test account was deactivated. The four named person accounts are
active and were handed over through an ignored owner-only credentials file. Johan
subsequently confirmed that he signed in and chose his own password. That personal
password is not known to the agent; later releases must preserve it. Other members
still need to use their own credentials and record their observations. No agent
assertion supplies their acceptance or an independent code review.

See [release evidence and remaining limits](verification-2026-11-17.md).
