# delopgave2-iot-mvp

The group's Delopgave 2 project for Intelligent IoT Solutions: a REST API for
predictive maintenance/notification, a separate database and CI/CD.

## Current status

The repository contains shared agent/developer guidance and setup validation.
**No application, database, application dependencies or deployment are implemented yet.**
The wider maintenance design is context, not a list of features already built.
The agreed prototype covers **Predictive Maintenance only**, with an English
technician dashboard, synthetic sensor history, simulated forecasts and a labelled
simulated outcome for case resolution. Better Maintenance is excluded.
Preparation is documented; application implementation has not been authorized yet.

- [Project status, intended boundaries and open decisions](docs/project-context.md)
- [Agreed prototype scope, walkthrough and acceptance examples](docs/prototype-plan.md)
- [Course requirements and source register](docs/course-context.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Using Codex, Claude Code, Cursor or Copilot](docs/agent-setup.md)
- [Canonical agent instructions](AGENTS.md)
- [AI-use record](docs/ai-use.md)

## Get started

Accept the GitHub invitation, then clone this repo or update your existing clone.
Open the `delopgave2-iot-mvp` folder itself in your editor/agent. Each member uses
their own account and tool; no API key or paid agent service is needed by this setup.

Use Git and Python 3.10+ for the setup checks (no pip install required):

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/check_repository.py
git diff --check
```

On Windows, substitute `python` or `py -3` for `python3` as installed.
The GitHub Actions job **Repository checks** runs these on pushes and PRs.
It validates repository guidance, not API functionality. Application setup and
validation commands must be added when the first application increment is built.
See the contribution guide before starting a task branch.
