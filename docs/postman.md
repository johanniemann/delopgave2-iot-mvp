# Demonstrate the API with Postman

The [collection](../postman/Aeris.postman_collection.json) contains 13 numbered
requests with 23 assertions. It demonstrates the selected Predictive Maintenance
flow and real PostgreSQL persistence using synthetic data. It creates a fresh
scenario each run and preserves previous cases; there is no reset/delete request.

## Run locally

1. Start the isolated local demo with `python3 scripts/observability.py up`.
2. In the Postman desktop app choose **Import** and select
   `postman/Aeris.postman_collection.json` from this clone.
3. Open **Aeris Predictive Maintenance walkthrough**. Its `base_url` defaults to
   `http://127.0.0.1:8766`, with no authentication for the loopback-only local app.
4. Choose **Run**, keep all 13 requests in order, use one iteration and enable
   **Keep variable values** for the later restart check. Expect all
   assertions to pass. Request 04 deliberately expects HTTP 409: the case is
   blocked until a human has reviewed the forecast.
5. Requests 09-12 show that a failed simulated verification leaves the case Open,
   while complete work and a passed simulated verification resolve it. No actual
   turbine is repaired and Better Maintenance is not implemented.
6. Request 13 reads the complete saved case again and compares it with request 12.
   Keep the same Postman variables, restart the local app/database without deleting
   volumes, then send request 13 alone to demonstrate persistence across a restart.

The scripts generate request IDs and refresh the scenario version between changes.
Do not skip the version-refresh requests. Re-running the entire collection creates
a new scenario; sending request 13 alone reads the last case instead.

The original uninstrumented local demo uses port 8765. To use that installation,
change `base_url` explicitly. It has separate data from the isolated port-8766 demo.
The web app needs the Postman Desktop Agent to call localhost; the desktop app can
call it directly. A cloud runner/monitor cannot reach this Mac's loopback service.

## Shared Azure demonstration

The shared VM must first be started deliberately. Set `base_url` to
`https://aeris-studiegruppe-linux.swedencentral.cloudapp.azure.com` and change the
collection's Authorization to **Bearer Token**. Reference a secret in your
**Postman Local Vault**, for example `{{vault:aeris-demo-token}}`. Each member enters
the privately supplied access token in their own local vault. Do not put its actual
value in collection variables, Git, URLs, screenshots or a synchronized environment.
Request 01 is public readiness; all `/api` calls require the shared token.

No Azure deployment or always-on Postman monitor is created by this collection.
Stop/deallocate the VM after a shared demonstration, preserving its disks/volumes.

## Version and validation

The repository JSON is the portable source. A copy was created in the owner's
team-visible Postman workspace:
[Aeris collection](https://go.postman.co/collection/60047103-624311ec-9612-49ab-9207-a66736f8fb4a). GitHub collaborator access does not itself grant
Postman workspace membership; teammates can import the same JSON into their own
workspaces without buying a shared plan or changing repository visibility.

On 2026-11-08 Newman 6.2.3 executed the collection against the actual isolated local
FastAPI/PostgreSQL service: 13 requests, 23 assertions, zero failures. This is a
local run, not evidence that another group member has tested access or that the
Azure VM has received this branch. To repeat the command with Node/npm installed:

```sh
npx --yes newman@6.2.3 run postman/Aeris.postman_collection.json
```

Meaningful collection changes should be run again and reviewed through a PR.
Keep the app's OpenAPI and [API contract](api.md) authoritative for request shapes;
update the collection when those contracts change. This supports the Postman/API
and persistence demonstration in course sources A1/A2, not a separate requirement
to use a commercial Postman plan. See [course context](course-context.md).

Official references checked 2026-11-08:
[importing collections](https://learning.postman.com/docs/getting-started/importing-and-exporting/importing-data/),
[Postman Local Vault](https://learning.postman.com/docs/use/postman-vault/postman-vault-key/),
[Collection Runner settings](https://learning.postman.com/docs/tests-and-scripts/running-collections/intro-to-collection-runs),
and [Newman](https://github.com/postmanlabs/newman).
