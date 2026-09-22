# SmartGov AI — Master Prompt Audit and Repair Report

## Audit basis

Audited the supplied `SmartGov_AI_COMPLETE_MASTER_PROMPT(1).txt` against the current `GovScheme` project, including routes, models, database schema, AI services, automation, RPA, templates, JavaScript, CSS references, configuration and tests.

## Repaired gaps in this pass

1. Added `application_process` to the scheme data model with additive migration support.
2. Added official-source document requirement storage instead of guessing required documents.
3. Rebuilt document readiness so profile fields never count as proof of document availability.
4. Added a configurable authorized DigiLocker OAuth/document-metadata integration boundary without inventing provider endpoints.
5. Added OAuth state validation, connection states, expiry handling, metadata-only persistence and local disconnect.
6. Added official DigiLocker portal fallback when live configuration is unavailable.
7. Added scheme-specific document readiness to scheme details and application details.
8. Added chatbot document-readiness handling using the shared readiness service.
9. Added chatbot customer-care handling that checks actual application records before escalating.
10. Added chatbot complaint-response lookup for the latest stored admin response.
11. Added language confidence handling so low-confidence automatic detection asks the user to choose a language.
12. Added separate STT/TTS capability reporting and stopped the browser widget from claiming unsupported voice languages.
13. Added `india_gov` as an explicit official discovery source and implemented conservative link-only discovery from the official India.gov scheme catalogue.
14. Added `OUTDATED` detection when an operator explicitly declares an official feed to be a complete catalogue.
15. Changed updated trusted schemes to remain unchanged until an administrator explicitly approves the pending source candidate.
16. Stored the complete pending source candidate payload for admin review.
17. Re-evaluate eligibility and refresh persisted recommendations only after a verified update is approved.
18. Prevented database startup seeding from silently overwriting already verified scheme records.
19. Added the missing admin UI for discovery source and refresh interval selection, including India.gov.
20. Removed explicit placeholder wording from the UiPath documentation and clarified the live/manual boundary.

## Still configuration-dependent by design

- Live DigiLocker access requires an authorized integration and its supplied endpoints/client configuration.
- Live Azure STT/TTS requires configured credentials.
- Live UiPath requires a configured tenant, published/reviewed process and permitted target portal.
- Real password-reset email requires SMTP/app-password configuration.
- An approved machine-readable government feed is required for JSON-feed discovery. India.gov HTML discovery is available as an official source path but remains conservative and candidate-based.

## Verification completed in this build environment

- Python `compileall`: PASS.
- Project preflight: PASS, 70 routes, 0 errors, 0 warnings.
- Fresh SQLite schema creation: PASS, including new document/DigiLocker tables.
- Excel database build: PASS, 20 schemes loaded.
- Verified scheme preservation across database rebuild: PASS.
- New candidate insertion: PASS and remains `PENDING_REVIEW`.
- Updated candidate handling: PASS; verified source record is not overwritten before approval.
- India.gov parser safety test: PASS; only India.gov scheme links are accepted.
- Language detection confidence test: PASS for Hindi/Bengali/Assamese and low-confidence Latin input.
- UiPath Studio execution: NOT TESTED because UiPath Studio/Robot is unavailable in the build environment.
- Full Flask pytest suite: NOT EXECUTED here because Flask/Werkzeug are not installed in this isolated build environment. Run it in the project's configured virtual environment.
