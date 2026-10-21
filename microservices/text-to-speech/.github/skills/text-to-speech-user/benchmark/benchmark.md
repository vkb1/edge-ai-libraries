<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Skill Benchmark: text-to-speech-user

**Agents**: Copilot (`claude-sonnet-5.5`)  
**Grader**: Copilot (`claude-sonnet-5.5`)  
**Date**: 2026-10-21T08:37:46Z  
**Evals**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 (1 run per configuration)

## Summary

> Skill lift = with skill − without skill. ↑ = better, ↓ = higher cost (expected).

### Evals passed

| Agent | w/o skill | w/ skill | Lift |
|---|---|---|---|
| Copilot (`claude-sonnet-5.5`) | 0 / 13 | 0 / 13 | **+0** |

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
| 1 | I want to generate a WAV greeting for my kiosk app from the text 'Welcome, pleas... | n/a | n/a |
| 2 | My app currently calls OpenAI's real text-to-speech API and requests response_fo... | n/a | n/a |
| 3 | I'm sending {"model": "tts-1-hd", "input": "Hello"} expecting this service to lo... | n/a | n/a |
| 4 | My team told me our text-to-speech deployment uses Qwen3-TTS with voice_design, ... | n/a | n/a |
| 5 | I want to stream longer narration text so playback can start before the whole th... | n/a | n/a |
| 6 | A streaming request for a string that's just a bunch of punctuation marks (somet... | n/a | n/a |
| 7 | I don't know whether the currently running deployment is SpeechT5 or Qwen, and I... | n/a | n/a |
| 8 | I requested voice: 'Morgan' against a SpeechT5 deployment and got a 400 error in... | n/a | n/a |
| 9 | I set "device": "NPU" in my request to POST /v1/audio/speech, expecting it to ju... | n/a | n/a |
| 10 | I called GET /v1/audio/voices expecting fields named speakers and languages like... | n/a | n/a |
| 11 | I requested voice: 'Morgan' against the default Kokoro deployment, expected an H... | n/a | n/a |
| 12 | My client sends a 6000-character input string to POST /v1/audio/speech expecting... | n/a | n/a |
| 13 | The deployment has pipeline.persist_outputs set to true. I'm using POST /v1/audi... | n/a | n/a |
| | **Mean ±σ** | n/a | n/a |