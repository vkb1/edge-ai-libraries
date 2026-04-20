<!--
SPDX-FileCopyrightText: (C) 2025 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Copilot Instructions

## Scope

These instructions apply to the entire `edge-ai-libraries` repository.

## Project Context

- **Edge AI Libraries** is Intel's repository for building and deploying real-time AI solutions on edge devices.
- It contains **libraries**, **microservices**, **frameworks**, **tools**, and **sample applications** optimized for Intel CPUs, GPUs, and NPUs.
- The companion repository **edge-ai-suites** provides industry-specific sample applications that depend on components from this repository.
- License: Apache-2.0. Every source file must include an Apache-2.0 SPDX header.

## Repository Structure

```
edge-ai-libraries/
├── libraries/          # Core AI libraries (anomalib, dlstreamer, edge-control, robotics-ai, etc.)
├── microservices/      # Deployable microservices (time-series-analytics, model-registry, audio-analyzer, etc.)
├── frameworks/         # Edge device enablement framework
├── tools/              # Evaluation and monitoring tools
├── sample-applications/ # Sample apps (chat-qa, document-summarization, etc.)
└── .github/            # CI/CD workflows, actions, templates
```

## General Coding Rules

### Python

- Target Python 3.11–3.13 depending on the component.
- Use type hints for all new and modified function signatures.
- Use `logging` module (never `print()` in production code).
- Use `async`/`await` for FastAPI route handlers and async libraries.
- Use Pydantic models for request/response validation where FastAPI is used.
- Pin dependency versions in `requirements.txt` files.

### Dockerfile

- Use multi-stage builds to minimize image size.
- Run as a non-root user (never `USER root` in the final stage).
- Include a `HEALTHCHECK` instruction.
- Drop all capabilities and set `no-new-privileges` in security contexts.
- Follow existing Hadolint conventions; address DL and SC warnings.

### Helm Charts

- Use semantic versioning for `Chart.yaml` (e.g., `2026.1.0-helm`).
- Enforce security contexts: `readOnlyRootFilesystem`, `runAsNonRoot`, `drop: [ALL]`.
- Template all configurable values through `values.yaml`.

### Shell Scripts

- Write POSIX-compatible shell scripts where possible.
- Pass ShellCheck validation (SC error codes).
- Include proper error handling with `set -e` or equivalent.

### YAML / Workflows

- Pin GitHub Actions to full commit SHAs (not tags).
- Follow the principle of least privilege for `permissions`.
- Use `persist-credentials: false` on checkout actions.

## Compliance Requirements

- **License Header**: Every source file (`.py`, `.sh`, `.yaml`, `.yml`, `.js`, `.ts`, `.c`, `.cpp`, `.h`, `.hpp`) must have an Apache-2.0 SPDX license header.
- **No Secrets**: Never commit passwords, tokens, API keys, or credentials. Use GitHub Secrets or environment variables.
- **Third-Party Dependencies**: When adding new dependencies, declare them in the PR with name, version, and license. Ensure compatibility with Apache-2.0.
- **Security Scans**: All code must pass CodeQL, Bandit (Python), Trivy (container), and Pylint checks that run in CI.

## CI/CD Patterns

- Workflows are path-filtered to only trigger on relevant component changes.
- Reusable workflows (`workflow_call`) are used to compose CI pipelines.
- Scans include: CodeQL (SAST), Bandit (Python security), Trivy (filesystem/image/config), Pylint, ShellCheck, Hadolint, ClamAV (virus), Docker Bench Security.
- Unit tests use `pytest` with `pytest-cov` for coverage.
- Functional tests run in Docker Compose and/or k3s (Kubernetes) environments.

## PR Guidelines

- Follow the PR template: description, dependency declaration, testing evidence, compliance checklist.
- Keep changes focused—do not mix unrelated refactors.
- Ensure existing unit tests and functional tests pass before submitting.
- Review CODEOWNERS for the component you are modifying to understand required reviewers.

## Validation Before Finishing

- Run relevant unit tests (e.g., `./tests/run_tests.sh` for the component).
- Run linters: `pylint` for Python, `shellcheck` for shell, `hadolint` for Dockerfiles.
- For docs-only changes, verify documentation builds successfully.
- Do not include unrelated refactors in the same PR.
