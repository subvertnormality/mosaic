# Source-of-truth migration proposal · deferred until pilot review

The pilot adds authored scene data without changing the present authority of README.md, AGENTS.md, cheat_sheet.html or manual-inventory.json. Replacing their authority before every feature is migrated would leave the instrument documented only in part.

After approval to scale:
1. Review every inventory entry; author its stable feature ID, prose, controls, interactions and verified scenes.
2. Add feature-ID citations alongside existing requirement IDs. Preserve requirement/case identity and original baseline hashes.
3. Teach inventory, coverage and gate tooling to resolve manual feature IDs and hash all authoring files. Add rejection tests for missing IDs, stale hashes and incomplete scene bindings.
4. Generate quick reference from the same feature model; keep the old URL.
5. Replace README with overview, install and first sound; update AGENTS authority and documentation-capture instructions together.
6. Check the complete combined campaign inventory without relabelling historical README evidence.

This is a large coordinated migration and is intentionally a proposal for the pilot review. No approval to push, open a PR or publish has been requested or assumed.
