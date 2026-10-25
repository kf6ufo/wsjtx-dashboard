# WSJT-X Dashboard: Merge Reviewed Features into Main

We are ready to establish a new stable `main` branch for the WSJT-X Dashboard.

The current Dashboard at http://127.0.0.1:8787/ is operating successfully. Wavelog historical QSO lookups are enabled and have been verified by the operator. Dashboard QSO submissions remain disabled, and the existing production WaveLogGate continues handling completed QSOs.

The operator approves merging the currently reviewed functionality into `main`, subject to final validation and preservation of all existing configuration and operating data.

## 1. Review Current Repository State

Before making changes:

- Read `AGENTS.md`, `WSJTX-REBUILD-HANDOFF.md`, `README.md`, `docs/current-checkpoint.md`, and `docs/roadmap.md`.
- Inspect the current Git branches, commits, working-tree status, and open pull requests.
- Confirm that PR #3 and PR #4 still contain the expected changes.
- Check for uncommitted work or newly introduced conflicts.
- Preserve any uncommitted work rather than discarding it.

The relevant pull requests are:

- PR #3: https://github.com/kf6ufo/wsjtx-dashboard/pull/3
- PR #4: https://github.com/kf6ufo/wsjtx-dashboard/pull/4

PR #3 contains the Step 4 station interface improvements.

PR #4 contains the independent ADIF history provider, Wavelog fallback, enriched QSO logging infrastructure, and durable delivery queue.

PR #4 is currently based on the Step 4 feature branch.

## 2. Preserve the Existing Installation

The currently running Dashboard is the single instance at:

http://127.0.0.1:8787/

Before performing any upgrades, restarts, or branch changes:

- Identify the actual running process and serving checkout.
- Back up the current `config.toml`.
- Back up the complete application `data` directory, including SQLite databases and any pending delivery records.
- Preserve the 86 previously reported Focus History entries and all subsequent entries.
- Preserve existing station settings, rig identities, QRZ/Wavelog credentials, UI preferences, and photo information.
- Preserve any configured ADIF files.
- Record the current commit and maintain a rollback path.

Do not create another permanently running Dashboard instance.

Do not modify, restart, stop, or reconfigure production Wavelog, WaveLogGate, or WSJT-X.

## 3. Perform Final Validation

Run the appropriate existing test suites before merging:

- Python backend tests
- Vue/TypeScript frontend tests
- Production frontend build
- Existing browser integration workflows
- Wavelog read-only history tests
- ADIF history and fallback tests
- Enrichment and duplicate protection tests
- Durable logging queue and recovery tests
- Multiple WSJT-X instance tests
- Native installation and upgrade-preservation checks where practical

Check that the existing UI remains functional, including:

- Station profile and photographs
- Two-column station details
- Zoomable station map
- Worked-before indicators
- Previous QSO history
- Shared Focus History
- Multiple rig identities
- Settings and diagnostics

Verify that Wavelog history integration remains enabled for the current installation.

Do not interpret a successful mocked API test as proof of real Wavelog write acceptance.

If tests or merge checks fail, fix relevant issues on the appropriate feature branch and repeat validation before merging. Stop and report any unresolved blocking issue.

## 4. Merge Pull Requests in Dependency Order

Once validation succeeds:

**First: PR #3**

- Complete the draft review status as appropriate.
- Merge `feature/step-4-station-details` into `main`.
- Confirm the merge succeeded.

**Second: PR #4**

- Update PR #4 to target the newly updated `main`.
- Verify that the resulting diff contains only the expected QSO history, enrichment, and logging infrastructure changes.
- Resolve conflicts if necessary, preserving the approved implementation.
- Rerun affected tests.
- Complete the draft review status as appropriate.
- Merge PR #4 into `main`.

Do not force-push or rewrite published history unnecessarily.

Verify that `main` contains both sets of functionality and that the resulting Git history is consistent.

## 5. Verify the Running Dashboard

After merging, bring the existing single Dashboard installation into alignment with the new `main` branch.

Use the supported installation/upgrade procedure and preserve all operating configuration and data.

If an application restart is required, perform a controlled restart of the Dashboard only.

Confirm:

- Dashboard responds at http://127.0.0.1:8787/
- Only one Dashboard instance is running
- Existing configuration is preserved
- Focus History remains intact
- Wavelog historical QSO lookups work
- QRZ and pyhamtools enrichment remain available
- WSJT-X UDP reception continues functioning
- No unexpected browser or backend errors occur

Do not assume a successful restart alone establishes functional correctness.

## 6. Preserve Production Logging Safety

This requirement is mandatory.

The new Dashboard completed-QSO logging feature must remain **disabled**.

In particular:

- `logging_enabled = false`
- `log_to_wavelog = false`

Do not enable Dashboard QSO submission to production Wavelog.

Do not send experimental QSOs to production Wavelog.

Do not perform experimental retry, duplicate-submission, or outage testing against production Wavelog.

Do not disable or replace WaveLogGate.

The existing WaveLogGate remains responsible for production QSO submissions until the operator explicitly approves cutover.

The absence of an isolated Wavelog test instance must not prevent merging correctly disabled, otherwise validated logging infrastructure.

## 7. Update Project Documentation

After the successful merge, update the handoff, roadmap, and checkpoint documents to reflect the actual state.

Record:

- Steps 0–4: current implemented and reviewed status, distinguishing any remaining unverified requirements
- Step 5: remaining Focus History enhancements
- Step 6: logging infrastructure implemented, but production submission/cutover not yet approved
- Step 7: UDP forwarding not yet implemented

Do not mark Step 5 fully complete unless all its acceptance criteria have been met.

Do not mark Step 6 operationally complete until real Wavelog submission validation and production cutover have occurred.

Document the successful merge commits, verification results, runtime configuration, and remaining work.

## 8. Final Acceptance Report

When finished, provide a concise report containing:

1. PR #3 merge result and commit
2. PR #4 merge result and commit
3. Current `main` commit
4. Tests executed and their results
5. Dashboard status at port 8787
6. Confirmation that existing configuration and history were preserved
7. Confirmation that Dashboard logging remains disabled
8. Confirmation that WaveLogGate remains unchanged
9. Any known limitations or outstanding validation requirements

If any merge, validation, or deployment step cannot be safely completed, explicitly report the blocker instead of claiming completion.

## Final Objective

Establish a clean, stable, reviewed `main` branch containing the existing WSJT-X Dashboard features and the new optional QSO history/logging architecture.

Preserve the current working Dashboard and all user data.

Leave production QSO submission unchanged.

Once this baseline is established, future development will focus on:

- Completing remaining Step 5 Focus History enhancements.
- Step 6: validating and activating enriched Wavelog/ADIF logging, eventually replacing WaveLogGate.
- Step 7: implementing configurable UDP forwarding to compatible third-party logging applications.

Do not begin new feature development as part of this merge task.

The objective is a verified, stable project baseline, not an expansion of scope.
