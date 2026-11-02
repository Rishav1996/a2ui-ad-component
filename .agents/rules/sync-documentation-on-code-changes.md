# Rule: Mandatory Documentation Synchronization on Code Changes

Whenever any code changes, refactors, new features, or architectural adjustments are made to the codebase, the agent MUST immediately identify and update all corresponding documentation files to maintain 100% synchronization.

## 1. Code-to-Document Mapping Rules

1. **Multi-Agent & Auction Architecture Changes**:
   - *Trigger Files*: `google_a2a_agent/agents/*`, `google_a2a_agent/auction/*`, `google_a2a_agent/callbacks.py`, `google_a2a_agent/runner.py`.
   - *Mandatory Doc Updates*:
     - `README.md` (Architectural diagrams, scenario showcase, paradigm table).
     - `docs/ARCHITECTURE.md` (System design, sequence flows, lifecycle callbacks).

2. **File Tree, Modularization & Directory Structure Changes**:
   - *Trigger Files*: Creating, deleting, renaming, or relocating any files or modules.
   - *Mandatory Doc Updates*:
     - `docs/DIRECTORY_STRUCTURE.md` (Directory tree, module descriptions, entrypoints).
     - `README.md` (Directory layout section).

3. **API Endpoints, Server & Frontend Changes**:
   - *Trigger Files*: `web_app/server.py`, `web_app/static/*`, `run_adk_server.py`, `api/index.py`.
   - *Mandatory Doc Updates*:
     - `README.md` (Quick-Start Guide, server endpoints, streaming protocols).

4. **Catalog & A2UI v0.9 Component Schema Changes**:
   - *Trigger Files*: `catalogs/*`, `renderers/*`.
   - *Mandatory Doc Updates*:
     - `README.md` (A2UI schema references).
     - `docs/ARCHITECTURE.md` (A2UI component specifications).

5. **Releases, Versioning & Packaging Changes**:
   - *Trigger Files*: `pyproject.toml`, `requirements.txt`.
   - *Mandatory Doc Updates*:
     - `CITATION.cff` (version, date-released).
     - `README.md` (BibTeX citation block, badge metadata, release changelog).

## 2. Invariant Checklist Before Task Completion
Before concluding any task involving code modifications:
- [ ] Inspect `git diff --stat` to review all touched modules.
- [ ] Determine which documentation files in `README.md` or `docs/` describe those modules.
- [ ] Update the documentation with exact, truthful descriptions matching the new implementation.
- [ ] Ensure all diagrams, code blocks, and references remain valid and accurate.

