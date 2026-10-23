# Current rebuild checkpoint

Date: October 23, 2026. Authority: [complete rebuild handoff](../WSJTX-REBUILD-HANDOFF.md). Branch: `rebuild/step-0`. Step 0 implemented; validation in progress before review. Steps 1–7 are the [roadmap](roadmap.md), not active integrations.

Predecessor preserved at `preserve/pre-rebuild-20261023` (`c93fce8`); the previously untracked user handoff was committed as `0affa60` before implementation. No history was rewritten, and no production station process/configuration was changed. Historical receiver evidence is in [validation history](validation-history.md) and does not validate the rebuild.

The installed path is `./install.sh` then `.venv/bin/python -m backend.server`, default URL http://127.0.0.1:8787/. Native foreground operation is common to macOS/Ubuntu. Server serves the built Vue frontend and refuses UDP enablement. Browser preferences, sample selections/history and provenance persist in ignored `data/workspace.sqlite3` next to `config.toml`; settings are validated and pushed over SSE. Sample profiles/contacts load independently with stale-response guards. Browsing is global and preserves selection order/provenance. External providers/submission/forwarding are not connected/implemented.

Actual macOS clean-checkout build, two-browser checks, restart/update preservation and results will be recorded here after completion. Ubuntu install/startup/service/UDP behavior is untested for the rebuild. No Step 1 implementation is authorized before Step 0 review.
