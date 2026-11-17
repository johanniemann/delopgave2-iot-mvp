# Account, evidence and backup data handling

## Purpose and responsibility

Aeris supports the study group's bounded Predictive Maintenance prototype,
technical demonstration and recovery practice. Turbine readings, forecasts and
maintenance outcomes are synthetic. Named accounts, review attribution and account
administration history concern real people and need separate care.

The group owns decisions about continued access and retained evidence. The Aeris
Admin manages application accounts; an explicitly authorized host operator manages
private settings, database backups and recovery. An Aeris role grants no Azure,
SSH, database or GitHub access. Each contributor is responsible for private files
on their own computer. These operating procedures supplement the implemented
controls; they are not an automatic retention or deletion service.

## Collect only what the prototype needs

| Data | Purpose and implemented boundary |
| --- | --- |
| Account UUID, username, display name, role, active/forced-change status, version and timestamps | Individual access and administration. No email, phone, address or external identity profile is required. Passwords are stored as Argon2id hashes, never returned by account APIs. |
| Session token hash, CSRF token and session timestamps | Server-side login, CSRF protection and expiry. The browser receives an opaque HttpOnly session cookie. Session secrets must not appear in screenshots, logs or exported collections. |
| Hashed login-limit keys, attempt counts and window times | Bounded sign-in throttling. Raw usernames/IPs are not stored in this table, but hashes and associated account evidence still belong in the private database. |
| Saved reviewer UUID/name, decisions, notes and domain timestamps | Explain who reviewed synthetic evidence and preserve the case's history. All authenticated workspace members can read this evidence. Enter only task-relevant synthetic notes; no customer details, passwords or unrelated personal information. |
| Account audit actor/target UUID, action, bounded change details and time | Explain administrative changes. The administration API is Admin-only; it does not return passwords/session tokens. Deactivation preserves the account identity behind historical evidence. |
| Security rejection logs and optional local telemetry | Security logs retain bounded method/route/status/time and an authenticated UUID when available. Telemetry retains bounded HTTP timing/count/status fields. Request bodies, credentials, raw URLs/queries and peer IPs are not copied by these app components. See [API](api.md) and [observability](observability.md). |

Use one personal Aeris account per member and a separate temporary account for
tests. Admin can correct a display name or reset access through the supported UI.
Saved reviews retain their original historical identity; changing a name does not
silently rewrite old evidence. Do not add customer or physical-sensor data to this
prototype without a separate decision about purpose, access and handling.

## Access and private copies

Only Admin can list/manage application accounts or read administration history.
Technician and Admin both work in the same maintenance workspace; there is no
per-user case ownership or tenant isolation. Keep that shared visibility in mind
before entering a note or exporting an evidence response.

Private `.env` and credential files stay outside Git, Docker build context,
synchronized Postman environments and recordings. Hand over each temporary password
privately to its recipient, who chooses a personal password at first login. Once
handover and password change are confirmed, the authorized owner reviews/removes
obsolete temporary credential copies. Do not delete a member's only handover copy
before they can access their account.

Private database dumps contain **the full account/session/audit tables**, including
session CSRF material and password hashes, even though turbine data is synthetic.
Use owner-only directories (0700) and files (0600), restrict copies to authorized
operators, and retain an additional private off-host copy only through the agreed
transfer procedure. A same-disk dump does not protect against losing the VM disk.
Do not print dumps, credential files or database identity tables in a demonstration.
The [release guide](release.md) describes checksum and isolated-restore verification.

## Review access and retention at closure

At the end of Delopgave 2, before reusing its data/accounts for an exam project, and
at the end of any continued project, the group and authorized operator must:

1. Review active accounts and deactivate temporary/test accounts and members who
   no longer need access. Preserve the last active Admin until the installation is
   deliberately retired. Deactivation revokes sessions; account rows and historical
   attribution remain.
2. Select only the evidence and recovery copy still needed for the agreed project
   purpose. Review whether names are necessary in shared screenshots/exports;
   remove unrelated personal information before sharing. There is no built-in
   anonymizing export, and a raw case response can contain reviewer identity.
3. Record the responsible owner, reason for each retained private copy and next
   review date in a private operator record. Review old dumps, one-time account
   inputs and temporary credential files; remove redundant copies only after
   confirming the selected evidence and a usable current backup remain available.
4. Decide explicitly whether to keep the installation stopped for further practice
   or retire it. Deallocation preserves disks/data; it does not delete them.
   Deleting shared volumes, backups or cloud resources requires a separate concrete
   decision and must preserve any evidence the group has agreed to keep.

No scheduled account, case, audit or backup purge is implemented. Sessions expire
after eight hours absolute or thirty minutes idle; expired-row cleanup occurs on
later sign-ins. Old throttle rows are cleaned on later login attempts. These
mechanisms do not remove account, review or administration history, nor old dumps.
Container log rotation bounds space rather than enforcing a retention period.

A live database restore is a separate maintenance operation from the helper's
isolated test restore. A full dump can reintroduce old passwords, active accounts
and sessions. Before returning a restored installation to users, the authorized
operator must invalidate restored sessions and review account access. Do not
describe a verified isolated restore as an already completed live recovery.
