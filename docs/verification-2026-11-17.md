# Verified technical release — 2026-11-17

This records observed results, not a claim of independent group review or production
readiness. Synthetic readings, deterministic illustrative forecasts and simulated
external maintenance outcomes remain explicit. Only Predictive Maintenance is built.

## Traceability

- [PR 12](https://github.com/johanniemann/delopgave2-iot-mvp/pull/12) integrated the
  technical audit improvements into dev; Denstoerste merged it. No formal independent
  review submission was present. The user approved continuing this concrete release.
- [PR 13](https://github.com/johanniemann/delopgave2-iot-mvp/pull/13) promoted dev to
  main after all checks passed, including GitGuardian. Main commit `16db954cb978437de8096c826fdcdca82bb147b4`
  passed [application run 44074754506](https://github.com/johanniemann/delopgave2-iot-mvp/actions/runs/44074754506).
- The actual trusted publish job succeeded. GitHub's package page showed the exact
  main tag and **Private** visibility. The downloaded image/source artifact matched
  GitHub's SHA256 `cb409025f34baf28e0e5fc2ec42b8737abd37f1cc23564721015641d6dda6911`,
  its source revision and both archive checksums before transfer to the VM.
- The exact tested Linux/amd64 image was loaded without rebuilding. Runtime health,
  Docker image revision and database readiness matched that source commit.
- Final host verification detected a relative-path defect in the release pointer;
  [PR 16](https://github.com/johanniemann/delopgave2-iot-mvp/pull/16) resolves the
  release root before changing directory. The regression failed before the fix and
  passed afterwards. The running image/data were correct; the stale pointer was
  repaired after checking its old and new targets. Follow-up promotion uses the fix.

Final selected release: `0f1e9d82a2ee36f687292b3781dd7778b6283364`, from
[PR 17](https://github.com/johanniemann/delopgave2-iot-mvp/pull/17) and successful
[main run 44077195363](https://github.com/johanniemann/delopgave2-iot-mvp/actions/runs/44077195363).
The corrected main artifact matched GitHub SHA256
`5553f0dab758a2e60c6b1101ee6b907fdf8793e0fa1ecebfa14234c48d321bce` and both
archive hashes. A fresh restore-verified backup included Johan's personal password
change. The corrected tool then promoted the tested image with relative CLI paths;
external HTTPS revision, running image and shared current pointer all matched,
with no nested pointer. Domain/account fingerprints remained unchanged and the
QA account remained inactive. Application code is unchanged by this operations fix;
full remote Newman ran on the first release, while the correction passed its full
CI suite and a fresh external/runtime/pointer/preservation check.

## Tests and their practical meaning

| Observed check | Result | What it establishes |
| --- | --- | --- |
| Actual PostgreSQL application tests | 73 passed | Domain gates, persistence, accounts, invalid input, concurrency and privacy regressions |
| Helper/release tests after pointer fix | 24 passed | Archive/backup guards, private runtime settings and relative promotion pointer |
| Local HTTP smoke | Passed | A running app/database with authentication and role denial |
| Local Newman | 27 requests,46 assertions,0 failures | Saved API contract and sensor/case walkthrough against real HTTP |
| Azure HTTPS Newman | 27 requests,46 assertions,0 failures | Same walkthrough from the Mac to the VM with trusted TLS and real PostgreSQL |
| Bandit gate | No medium/high-severity findings at medium/high confidence | Selected SAST threshold; does not assert the absence of all vulnerabilities |
| pip-audit | No known runtime dependency advisories at execution | Locked runtime dependencies checked against then-current advisory data |
| Local controlled DB failure | Five expected 503s, then 200; complete case unchanged | Deliberate failure and recovery, not continuous uptime or an external alert service |
| Actual Azure app/database restart | Original four cases and new complete case identical | Persisted domain evidence survives those container restarts |
| Browser inspection | Individual login page observed on HTTPS | The sign-in view is present; full cross-browser acceptance is not established |

Direct Azure SQL verification after Newman found schema version 2, 579 readings,
5 cases and 43 events. The sensor windows were:

- Equality window `ab47192b-f18e-4812-900b-fcbe310a5ee2`: 28.0/Usable and zero incidents.
- Above-boundary window `b4850963-09f6-4bd1-b4c8-b7264579f567`: 101/Invalid and 28.1/Usable,
  exactly one incident, persisted recording events and `Fault Incident Opened`.
- New complete case `PC-29C3653D8F03`:96 synthetic readings, saved review, two
  simulated outcomes, resolved state and full event history. The failed outcome
  kept it open; the later complete passed result resolved it.

These counts are observations after a particular test, not fixed database invariants.
The threshold 28.0 m/s is a demonstration choice, not a validated turbine safety limit.

## Accounts and existing evidence

The user specifically approved Johan/Admin, Esben/Nix/Bilal/Technician and one
temporary Technician test account. Shared bootstrap created the initial Admin;
the API created individual accounts. Private random credentials were never printed
or committed. Temporary-password access, own password change, role denial 403,
CSRF 403, logout 401, edit revocation and administrator reset were actually tested
over external HTTPS. Anonymous and the old shared bearer both returned 401.

The test account was deactivated afterwards. The named person accounts were handed
over with a forced first-login password change. Johan then confirmed that he logged
in and chose his own password. Releases preserve account rows and passwords; the
agent does not know that personal password. Other members' own usage is still theirs
to demonstrate. No Azure/GitHub/host privileges were granted through Aeris roles.

Before migration the database had480 readings, 4 cases and 28 events. Complete JSON
baselines for all four cases matched after migration, after the real app/database
restart and after the new synthetic walkthrough. The stable volume remained
`aeris-shared_demo-data`; no shared reset or volume deletion was performed.

## Backup and recovery

Actual private `pg_dump` archives were restored into generated isolated databases;
table content fingerprints matched and only those generated test databases were
removed. The pre-migration backup has a checksum-verified private copy off the VM.
Fresh pre-migration and post-migration/account backups were also restored on the VM.
The additional full export was not performed after automatic approval review rejected
it; do not describe the post-migration copy as off-host protection.

Sessions and throttle rows are transient and excluded from content fingerprints;
domain, account and administration evidence is included. A named volume is not a
backup against host/disk loss. Recovery remains an explicit operator operation;
application rollback does not downgrade the schema or authorize token-only access.

## Security and operational limits

GitGuardian 40194040 matched an assertion's noncredential test marker. The user
approved classifying only that finding as false positive; provider incident/check
classification was applied and scanning remained enabled. Test markers are now
generated dynamically. Subsequent PR scans passed. This history is not a claim that
the original scanner never detected anything.

Dependabot alerts and security updates were enabled and observed. GitHub states
the saved main protection is not enforced under the current private-repository plan;
the normal review/merge rules are team conventions. No plan or visibility change
was used as a workaround. PR jobs receive no Azure/registry-write credentials.

The VM has bounded container/security logs and health checks, but no external uptime
monitoring or installed cloud SigNoz stack. Optional local SigNoz is separate.
Auto-shutdown 00:00 Copenhagen is saved; its actual midnight firing is not proven by
manual deallocation. The final Azure portal state was observed as **Stopped (deallocated)** after validation, so group
practice and recording require an intentional startup.

Still human work: independent code/content review, each member's own-computer
acceptance, a roughly five-minute recording, agreed examiner access to the private
repo, and critical assessment of the AI-assisted technical contributions. The [demo plan](demo.md)
is a runnable plan, not a recorded video.
