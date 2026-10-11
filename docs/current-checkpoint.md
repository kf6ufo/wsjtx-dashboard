# Current checkpoint for ChatGPT Work and VS Code/Codex
**Date:** 2026-10-11
**Status:** New repository configured. Milestone 1 has **not yet been implemented**.

## What is ready
- GitHub private repo: https://github.com/kf6ufo/wsjtx-dashboard (main).
- Project handoff: `docs/project-handoff.md`, source of product goals and phased architecture.
- Codex guardrails: `AGENTS.md`, source of implementation and production safety rules.
- README, Python .gitignore and MIT license in repository.
- Repository cloned on the user's Mac and opened in Visual Studio Code.
- VS Code initially opened the repository in Restricted Mode; user trusted workspace and the OpenAI Codex extension is now enabled and the Codex panel is open.
- No Milestone 1 code has been commissioned yet. User intends to switch from a normal ChatGPT chat to ChatGPT Work and continue working with local Codex in VS Code.

## Workflow
GitHub holds canonical versioned project files. Local Codex in VS Code edits the Mac working tree; changes must be reviewed, committed, and pushed for GitHub to receive them. Cloud Codex work may instead require review/merge from a remote branch. Work session should coordinate and review, not assume local VS Code files synchronize by magic.

## Immediate next step: Milestone 1, UI-first
Ask local Codex in VS Code to:
1. Read `AGENTS.md`, `docs/project-handoff.md`, and this checkpoint.
2. Implement a polished Vue 3 + TypeScript + Bootstrap 5 two-column dashboard with mock data.
3. Left: focused callsign, illustrative QRZ profile/photo placeholder, geographic info, full scrollable example QSO list.
4. Right: scrollable, clickable **deliberately focused** stations with thumbnails, originating rig and worked-before summary. Simulate multiple WSJT-X rigs.
5. Immediately update focus/history on a simulated selection, independently simulate delayed lookups and handle stale responses. Routine fake decodes must never steal focus.
6. Make a local browser preview with hot reload, add appropriate tests, and supply exact launch steps.
7. **Do not access live WSJT-X, Wavelog, QRZ, or transmit or submit QSOs.** Keep working WaveLogGate untouched.

## Verified integration background
Real WSJT-X Status `dx_call` changes were observed through multicast from Windows IC7300 and macOS QRPLabsQDX at `239.255.0.73:2238`. This supports a future live focus stage, but does not prove every Status change corresponds to a physical click. Wavelog is authoritative for complete QSO history. Initial releases focus on Wavelog (self-hosted or Wavelog Cloud), with no general logbook integrations necessary.

## Open decisions
Backend Python/FastAPI and `pyhamtools` are favored, but not needed for UI Milestone 1. SSE is planned for live browser updates, validated when backend arrives. QRZ photos are subject to actual access/permissions. Future Wavelog logging gateway must remain passive until separately verified under isolated tests.

## Local Codex first prompt
We're beginning development of WSJT-X Dashboard. Read AGENTS.md, docs/project-handoff.md, and docs/current-checkpoint.md. Implement only Milestone 1: a polished interactive Vue 3 + TypeScript + Bootstrap 5 two-panel dashboard using clearly marked mock data. Simulate independent WSJT-X rig selections, immediate shared focus and Focus History, delayed profile/QSO enrichment, and guards against stale responses. Include operator-friendly scrolling and clickable history, local hot-reload preview and tests. Do not connect to real radios, Wavelog, QRZ or production logging, and do not submit QSOs. Tell me precisely how to run and review it in my browser before moving on.
