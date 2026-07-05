<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# TSA Skills

Agent skills for the **Time Series Analytics (TSA)** microservice.
Each skill teaches the agent how to operate TSA through its real interfaces —
the REST API and UDF deployment package — so common tasks run the same way every time.

These skills live under `.github/skills` as the canonical cross-harness location.
They are plain Markdown workflows and can be used by Copilot, Codex, Claude Code,
or local agent scripts.

A skill is a directory with a `SKILL.md` (YAML front matter + workflow) and
optional `references/` (deep docs loaded only when needed) and `examples/`
(scenario walkthroughs).

## Cross-Harness Discovery

Tools that prefer structured metadata should read
[skill-catalog.json](./skill-catalog.json).
All catalog paths are relative to the repository root.

Keep the skill body in one place: update each `SKILL.md`, then keep the
catalog description and triggers in sync.

## Catalog

| Skill | Use it when the user wants to… |
|---|---|
| [`tsa-user`](./tsa-user/SKILL.md) | Deploy the service, upload a UDF, configure analytics, ingest data, check health |

## Conventions

- **Run commands yourself** and relay results; don't ask the user to run them.
- **Probe before acting.** Hit `GET /health` before any API workflow; if it fails,
  route to the service setup step.
- The default REST API port is **5000** (Docker Compose) or **30002** (Helm).
- Run repo-local commands from the repository root unless a skill says otherwise.
