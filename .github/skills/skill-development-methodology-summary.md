<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: 'Segoe UI', sans-serif;
    font-size: 1.05em;
    background: #ffffff;
    color: #1a1a2e;
    padding: 2em 3em;
  }
  h1 { color: #0071c5; font-size: 1.7em; border-bottom: 3px solid #0071c5; padding-bottom: 0.2em; margin-bottom: 0.4em; }
  h2 { color: #0071c5; font-size: 1.2em; margin: 0.3em 0 0.2em 0; }
  table { font-size: 0.82em; width: 100%; border-collapse: collapse; }
  th { background: #0071c5; color: #fff; padding: 0.4em 0.6em; }
  td { padding: 0.35em 0.6em; }
  tr:nth-child(even) { background: #f0f4ff; }
  code { background: #f4f4f4; padding: 0.1em 0.4em; border-radius: 4px; font-size: 0.9em; }
  blockquote { border-left: 4px solid #0071c5; padding-left: 0.8em; color: #555; font-style: italic; margin: 0.4em 0; }
  ul { margin: 0.3em 0; padding-left: 1.4em; }
  li { margin: 0.15em 0; }
---

# Skill Development Methodology

> *"You can't measure success if you haven't defined what success looks like before you start."*

### The 3-Phase Loop

| Phase | When | Owner | Purpose |
|---|---|---|---|
| **1 · Use Case Prompts** | Before building | Person with the problem | Define *why* the skill exists |
| **2 · Build the Skill** | During build | Skill developer | Implement scope from use case brief |
| **3 · Eval Prompts** | After building | Skeptic / tester | Prove the use cases are satisfied |

### Phase 1 — 5 Dimensions to cover per use case
`Core job` · `Input variation` · `Boundary / non-goals` · `Trigger phrase` · `Stakes if it fails silently`

### Phase 3 — Each eval prompt must be falsifiable
- **Must have** — what correct output contains
- **Must not** — non-goals become "must not" checks
- **Pass / Fail** — one measurable condition; a bad skill version must fail it

---

# The Two Hats Rule & Common Failure Modes

### Wear hats deliberately — never mix the phases

| Hat | Phase | Mindset |
|---|---|---|
| 🎩 Person with the problem | Use Case Prompts | *"I have a job. I don't care how it works."* |
| 🔍 Skeptic / tester | Eval Prompts | *"Prove to me this skill actually works."* |

### Common failure modes — and how the framework prevents them

| Failure mode | Use case prompts prevent it | Eval prompts catch it |
|---|---|---|
| Skill is too broad | Non-goals force explicit exclusions | Boundary evals fail if it wanders |
| Invoked for the wrong problem | Trigger phrasing grounds the description | Wrong-scenario evals produce noise |
| Output not actionable | Outcome must be actionable per use case | Eval checks structure, not just presence |
| Fails on edge inputs | Input-variation use cases expose this | Dedicated edge-case eval scenarios |
| Optimized for demos only | Stakes dimension forces real failure modes | Evals use failure scenarios, not happy path |

*SPDX-License-Identifier: Apache-2.0 | (C) 2026 Intel Corporation*
