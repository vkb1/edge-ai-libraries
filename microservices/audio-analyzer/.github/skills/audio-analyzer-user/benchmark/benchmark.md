<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Skill Benchmark: audio-analyzer-user

**Agents**: Copilot (`claude-sonnet-5.5`)  
**Grader**: Copilot (`claude-sonnet-5.5`)  
**Date**: 2026-10-21T08:29:34Z  
**Evals**: 1, 2, 3, 4, 5, 6, 7, 8 (1 run per configuration)

## Summary

> Skill lift = with skill − without skill. ↑ = better, ↓ = higher cost (expected).

### Evals passed

| Agent | w/o skill | w/ skill | Lift |
|---|---|---|---|
| Copilot (`claude-sonnet-5.5`) | 0 / 8 | 0 / 8 | **+0** |

### Pass rate (avg ± σ across evals)

| Agent | w/o skill | w/ skill | Lift |
|---|---|---|---|
| Copilot (`claude-sonnet-5.5`) | 0% ±0% | 0% ±0% | **+0pp** |

### Time (total across all evals)

| Agent | w/o skill | w/ skill | Lift |
|---|---|---|---|
| Copilot (`claude-sonnet-5.5`) | 0 s | 0 s | +0 s ↓ |

### Tokens (total across all evals)

| Agent | w/o skill | w/ skill | Lift |
|---|---|---|---|
| Copilot (`claude-sonnet-5.5`) | 0 | 0 | +0 ↓ |

## Per-Eval Detail

> Each cell is PASS/FAIL for that run, with the count of expectations met in parentheses (e.g. `PASS (5/5)`); `n/a` means no grading.json was found for that (eval, config, agent) combination.

| Eval | Prompt | Copilot (w/) | Copilot (w/o) |
|---|---|---|---|
| 1 | I have a recorded customer call saved as call_042.wav and I just want the full t... | n/a | n/a |
| 2 | I already use the official OpenAI Python SDK in my app for Whisper streaming tra... | n/a | n/a |
| 3 | My client uploads a subtitle file request with response_format=srt and stream=tr... | n/a | n/a |
| 4 | I want to build a live microphone transcription feature in my desktop app using ... | n/a | n/a |
| 5 | I'm streaming audio to /v1/realtime from a quiet lapel mic recording and input_a... | n/a | n/a |
| 6 | I want every uploaded chunk of a long file to produce a sentiment label so I can... | n/a | n/a |
| 7 | I set device=GPU as a form field when calling the NDJSON streaming endpoint /v1/... | n/a | n/a |
| 8 | My reconnect logic opens WS /v1/realtime?intent=transcription&session_id=../../e... | n/a | n/a |
| | **Mean ±σ** | n/a | n/a |