# Demonstrate the authenticated API with Postman

The [collection](../postman/Aeris.postman_collection.json) contains **27 requests and 46 assertions**. It signs in as a Technician, demonstrates the complete
Predictive Maintenance flow, verifies that user administration returns HTTP 403,
signs out and verifies HTTP 401. It creates a new synthetic scenario each run and
preserves all existing cases. It has no reset/delete request or committed credential.

## Run in the desktop app

1. Start `python3 scripts/observability.py up` (port 8766), or the normal local app
   on port 8765 followed by `python3 scripts/setup_accounts.py`.
2. Import `postman/Aeris.postman_collection.json` from **the selected release
   checkout**. A previously imported or synchronized workspace copy may be older;
   its current content has not been reverified here. Compare/reimport the reviewed
   collection rather than assuming a workspace copy matches the selected commit.
3. Set `base_url` to the chosen local origin. Set `login_username` to your Technician
   username. Keep the password in **Postman Local Vault**; reference it as
   `{{vault:aeris-password}}` in the login request's password value, replacing the
   `{{login_password}}` placeholder locally. Do not commit/export the actual value
   or put it in a synchronized environment. Each member uses their own account.
4. Run all **27 requests in order**, one iteration. Keep the cookie jar enabled.
   The login saves a transient CSRF token for subsequent writes; the session cookie
   is HttpOnly. The collection remains `noauth`: it now uses cookies, not Bearer.
5. Request 04 deliberately expects HTTP 409 until forecast review. Requests 09-12
   demonstrate failed and successful **simulated** outcomes and saved evidence.
   Request 14 deliberately expects HTTP 403 for the Technician's admin request.
   Requests 15-16 demonstrate logout and denial after logout.

New/reset accounts must choose their personal password in the dashboard first;
temporary credentials cannot run the business workflow. Enable **Keep variable
values** if you want to use the saved case ID/evidence after the run. To demonstrate
a restart, restart the app/DB without deleting volumes, send login 00 again and
then send request 13 alone. The full JSON must equal the saved evidence. Logging
out at the end means request 13 cannot be sent anonymously.

The two local app ports have separate data and credentials. The desktop app can
reach localhost directly; a cloud monitor cannot. The browser version needs the
Desktop Agent for localhost. No always-on monitor or public documentation is created.

## Repeatable local/CI run

With Node/npm installed, this helper reads only the selected private local account
file, writes a temporary mode-0600 Newman environment, and removes it after the run.
It does not put password values in command arguments, logs or the repository:

```sh
python3 scripts/run_postman.py --port 8766
```

Use port 8765 for the normal local app. GitHub Actions uses a fresh disposable
Compose project and newly generated local-only credentials, then executes the same
helper with Newman **6.2.3**. The Postman CLI is not installed in the verified Mac
environment; no CLI workspace/vault setup or lint result is claimed. Existing v2.1
collection/Newman support is retained without a format migration or paid service.

On 2026-11-08 the real local FastAPI/PostgreSQL service passed **17 requests,
28 assertions, zero failures**. The smoke check also verified anonymous rejection,
Technician login, admin denial and logout. These are real local HTTP results,
not proof that this branch is deployed to Azure or another member has tested it.

## Shared deployment

The account-based Azure release `0f1e9d82a2ee36f687292b3781dd7778b6283364` was
externally verified on 2026-11-17. Use the VM's HTTPS origin and your own
Technician account. Later feature candidates require separate promotion and
verification. The old shared token is no longer accepted. Secure
cookies require HTTPS. The VM must be deliberately started for a shared demo and
deallocated afterwards. See [account setup and limits](authentication.md) and
[deployment](deployment.md). GitHub collaborator access does not grant Postman
workspace access or an Aeris account.

Keep FastAPI's OpenAPI and [API contract](api.md) authoritative for request shapes;
update the collection through PRs when they change. Publish the reviewed collection
to the existing non-public workspace after merge, preserving its IDs and unrelated
requests. Never publish credentials or silently change workspace visibility.
This supports course A1/A2's API/persistence demonstration; Postman is not a mandate
for a commercial subscription. See [course context](course-context.md).

Official references checked 2026-11-08:
[importing collections](https://learning.postman.com/docs/getting-started/importing-and-exporting/importing-data/),
[Local Vault](https://learning.postman.com/docs/use/postman-vault/postman-vault-key/),
[Collection Runner](https://learning.postman.com/docs/tests-and-scripts/running-collections/intro-to-collection-runs),
and [Newman](https://github.com/postmanlabs/newman).


## External sensor demonstration (added 2026-11-17)

After request 13, the S01-S10 folder sends real HTTP sensor inputs into two empty
windows. In the first, 28.0 m/s is usable and does not open an incident. In the
second, km/h is rejected with 422, 101 m/s is retained as Invalid, and 28.1 m/s
opens an incident linked only to the usable reading. The collection verifies the
persisted readings, incident evidence and event facts. The original case flow and
its saved case variables are preserved.

Copy `sensor_scenario_id` from the collection's variables and inspect the same
rows using the internal database connection described in [the demo guide](demo.md).
Never open PostgreSQL publicly for the demonstration. Assessment freezes each
window, so equality/exceedance tests use different scenarios.

The expanded collection passed locally on 2026-11-17: 27 requests, 46 assertions,
zero failures against real FastAPI/PostgreSQL. Historical counts above describe
the earlier collection, not the current request total.
