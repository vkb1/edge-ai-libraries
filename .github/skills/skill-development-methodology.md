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
    font-size: 1.1em;
    background: #ffffff;
    color: #1a1a2e;
  }
  h1 { color: #0071c5; font-size: 1.8em; border-bottom: 3px solid #0071c5; padding-bottom: 0.2em; }
  h2 { color: #0071c5; font-size: 1.4em; }
  h3 { color: #444; font-size: 1.1em; }
  table { font-size: 0.85em; width: 100%; }
  th { background: #0071c5; color: #fff; }
  tr:nth-child(even) { background: #f0f4ff; }
  code { background: #f4f4f4; padding: 0.1em 0.4em; border-radius: 4px; }
  blockquote { border-left: 4px solid #0071c5; padding-left: 1em; color: #555; font-style: italic; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 1em; }
---

# Skill Development Methodology
## Use Case Prompts → Build → Eval Prompts

**The framework for building skills that actually solve real problems**

---

# The Core Problem

> Most skill builders start with *"what should this skill do?"*
> That is the wrong question.

### The right question is:

> *"What problem does someone have that makes them reach for this skill?"*

**You can't measure success if you haven't defined what success looks like before you start.**

---

# The Three-Phase Loop

```
Use Case Prompts       →    Skill Instructions     →    Eval Prompts
────────────────────────────────────────────────────────────────────
"Why am I building     →    "What does it do?"     →    "Did it work?"
 this?"

User perspective       →    Builder perspective    →    Measurable outcome

Written BEFORE         →    Written WHILE          →    Written AFTER
building                    building                    building

Defines scope          →    Implements scope       →    Validates scope
```

---

# Phase 1: Use Case Prompts
## Before you write a single instruction

Use case prompts are short, natural-language statements describing a **real situation** where someone would invoke this skill.

Written from the **user's perspective**, not the builder's.

### The "Why" Test

For each use case prompt, answer:
> *"What is the user trying to avoid or achieve?"*

If you can't answer that — the use case prompt isn't grounded enough.

---

# The 5-Dimension Framework

| Dimension | Question it answers | Example |
|---|---|---|
| **Core job** | Why does this skill exist at all? | "I need to review my Dockerfile before merging" |
| **Input variation** | Does it work across different inputs? | "I need to review a Helm chart, not code" |
| **Boundary** | Where does it stop being useful? | "Is my running cluster patched?" ← *out of scope* |
| **Trigger phrase** | How would someone actually ask? | "Can you check this PR for auth issues?" |
| **Stakes** | What goes wrong if it fails silently? | "I shipped an image with hardcoded credentials" |

---

# Non-Goals Are as Important as Goals

Explicitly list what the skill will **never** do.

This:
- Prevents scope creep during building
- Tells users when **not** to invoke it
- Becomes the basis for "must not produce" eval checks later

### Rule of thumb
If you can't clearly state two things the skill refuses to do — you don't understand the scope yet.

---

# Use Case Brief Template

```markdown
## Use Case Brief

### Why this skill exists
<One sentence: the pain/need it addresses>

### Use Cases
1. [Trigger]: <natural phrase> → [Outcome]: <what they get>
2. [Trigger]: <natural phrase> → [Outcome]: <what they get>
3. [Trigger]: <natural phrase> → [Outcome]: <what they get>

### Non-Goals (explicit exclusions)
- <What this skill will never do>
- <What belongs to a different skill>

### Failure mode
<What bad output looks like — missed findings, wrong scope, wrong format>
```

---

# Phase 2: Build the Skill

Only after use case prompts are written.

The use case brief maps **directly** to the skill:

| Use Case Brief section | Maps to Skill artifact |
|---|---|
| *Why this skill exists* | `description:` field — when to invoke |
| *Trigger phrases* | Trigger conditions / routing rules |
| *Inputs across use cases* | `inputs:` section |
| *Non-goals* | Explicit exclusions in instructions |
| *Outcome* | Output format and structure |
| *Failure mode* | What the skill must actively avoid |

---

# Phase 3: Eval Prompts
## After building

One eval prompt per use case.
Each is a **test case**: a concrete scenario + explicit pass/fail criteria.

### The key structure

```
Scenario:   <Specific, concrete version of the use case — real inputs>
Invoke:     <The skill, on that specific input>
Must have:  <What correct output contains>
Must not:   <What correct output never contains>
Format:     <Structural requirement on the output>
Pass when:  <The single measurable condition that means it worked>
Fail when:  <The condition that means the skill needs to be fixed>
```

---

# The "Must Not" List

This is where the **non-goals from Phase 1 pay off**.

For every non-goal → write a "must not" eval check.

If the skill produces output that crosses a non-goal boundary: **it fails**.

### Calibration Rule

> If your eval prompts can pass with a completely generic response (i.e., the skill isn't even invoked), the eval prompts aren't specific enough.

Each eval prompt must be **falsifiable** — a bad skill version should fail it.

---

# Example: Changelog Skill

| Use Case Prompt | Eval Prompt |
|---|---|
| "Generate changelog between v1.0 and v2.0" | Output must have a new `## [2.0.0]` section with Added/Fixed/Changed entries. No raw commit SHAs. |
| "What changed between main and release branch?" | Output is categorized markdown. Must not modify existing changelog entries. |
| "Update changelog for the whole repo" | Scans all commits. Output targets repo-root file. Must not be scoped to a subfolder. |

---

# Common Failure Modes

| Failure mode | Use case prompts prevent it | Eval prompts catch it |
|---|---|---|
| Skill is too broad | Non-goals force explicit exclusions | Boundary eval checks fail if it wanders |
| Wrong invocation | Trigger phrasing grounds the description | Wrong-scenario evals produce meaningless output |
| Output isn't actionable | "Outcome" must be actionable | Eval checks structure, not just presence |
| Fails on edge inputs | Input-variation use cases expose this | Dedicated edge-case eval scenarios |
| Optimized for demos | Stakes dimension forces real failure modes | Eval uses failure scenarios, not just happy path |

---

# The Most Important Habit

### When writing use case prompts:
> Put on the hat of **the person with the problem**.
> You are not the builder. You have no idea how the skill works.
> You just have a job to get done.

### When writing eval prompts:
> Put on the hat of **the skeptic trying to prove the skill doesn't work**.
> Your job is to find the scenario where it fails.

---

# Summary

```
1. Write 3–5 use case prompts
   → Defines WHY the skill exists and when to invoke it

2. Define non-goals
   → Prevents scope creep and becomes "must not" eval checks

3. Build the skill
   → Use case brief drives description, inputs, output format

4. Write one eval prompt per use case
   → Maps expected output back to each use case

5. Run eval prompts
   → If any fail, update the skill instructions

6. Repeat
   → Skills improve iteratively when evals are honest
```

---

# Key Principle

> **Use case prompts are written by the person with the problem.**
> **Eval prompts are written by the person who must prove it's solved.**

These are two different hats.
Wear them deliberately. Never mix the phases.

---
*Skill Development Methodology — Edge AI Libraries*
*SPDX-License-Identifier: Apache-2.0 | (C) 2026 Intel Corporation*
