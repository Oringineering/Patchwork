# Patchwork
[MIT licensed](LICENSE) · [Live demo](https://patchwork-demo.onrender.com/) · NVIDIA Nemotron on Nebius Token Factory

**Turn a bug report into a repair you can understand, review and take with you.**

Patchwork is a repair studio for students, maintainers and developers working on small codebases. A model-generated replacement alone leaves the reviewer to reconstruct its purpose. Patchwork bundles the target source, selected reference files, diagnosis, diff, syntax evidence, suggested tests and human decision into one portable review.

## What works
- Responsive landing page and dedicated studio with Overpass, Fira Sans and Fira Code typography.
- ZIP import, pasted source, searchable project files and two built-in examples with test context.
- Explicit context selection: up to five supporting files, 40 KB combined.
- NVIDIA Nemotron repair generation through Nebius Token Factory.
- Structured diagnosis, changes, risks and suggested regression tests.
- Deterministic Python / JSON syntax checks on original and proposed source.
- Overview, diff, replacement and suggested-test views.
- Accept or dismiss a repair. Acceptance is blocked if the source changed or the proposed syntax fails.
- Session review history, workspace ZIP export, unified patch export and JSON review report.
- Hosted server key, request limits, bounded model concurrency and clear error handling.

## Run locally
Requires Python 3.10 or newer. No Python dependencies are needed.

    python app.py

Open http://127.0.0.1:8000 in your browser. In Studio → Settings, enter your Nebius Token Factory secret. It stays in server memory, not browser storage. Alternatively set NEBIUS_API_KEY in the server environment. Do not commit credentials.

NEBIUS_MODEL defaults to nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B. If the catalogue changes, configure the exact available NVIDIA model ID in your Token Factory account.

The HTML depends on the Python API; opening index.html directly is not a supported way to use the app.

## Deploy on Render
The included render.yaml configures the existing Python service:
1. Connect this repository as a Blueprint or Python web service.
2. Set NEBIUS_API_KEY as a secret in Render.
3. Set PATCHWORK_DEMO_MODE=true. Start command: python app.py.
4. Render supplies PORT; hosted mode binds to 0.0.0.0.
5. Verify /api/status and make a live example repair.

A configured status means a key exists; it does not validate authentication. The Google Fonts stylesheet and fonts are allowed by a narrow CSP. System fonts are used if fonts cannot load.

## Architecture
Browser workspace → Python API → NVIDIA Nemotron via Nebius Token Factory → structured review → parser checks → human decision → export.

- GET /api/status: public configuration status and model ID, never credentials.
- POST /api/upload: inspect a ZIP and report skipped entries.
- POST /api/propose: send the target, bug report and chosen reference files for a repair review.
- POST /api/export: package supported workspace files into a ZIP.
- POST /api/config: configure a key in local mode only.

The application is hosted on Render; model inference runs on Nebius Token Factory. It does not claim to use Nebius Serverless Jobs or run arbitrary code on AI Cloud.

## Verification
Run the offline regression suite:

    python -m unittest test_app -v
    node --check studio.js

The Python suite covers structured model response validation with mocked replies, truncation, syntax failures, context budgets, archive filtering, exports, origin checks, hosted configuration and key privacy. It consumes no model credits. A successful mocked test is not evidence of a live model response.

## Current boundaries
- The model proposes one target-file repair at a time. Reference files are context, not additional edit targets.
- Uploaded/generated code and suggested regression tests are not executed. Syntax success does not prove behavioural correctness.
- Python and JSON get parser checks. Other languages are explicitly marked unchecked.
- ZIPs up to 2 MB; up to 40 supported text files; 300 KB per imported file, 1.5 MB total. The repair target is limited to 30 KB.
- Export contains supported workspace files only. Binary assets, dependency folders and skipped entries are not preserved.
- Workspace and history live in the current tab; refreshing clears them. Export before leaving.
- Source, report and selected context are sent to Nebius for inference. Patchwork does not save uploads to server disk; consult your provider terms for provider retention.
- This demo has no accounts or persistent project storage. Request limits are in-memory and reset on restart. Proxy deployments may share a client limit. Use an external rate-limit store before scaling.
- Cancellation stops the browser waiting; the server's model call can still finish and consume tokens.

## Hackathon
Best Apps and Agents is the proposed track for the current implementation. See [DEMO.md](DEMO.md) for a concise demonstration and judging checklist.

October 27 update: rebuilt the site and studio; added selected context, structured model reviews, parser evidence, decision handling, history, ZIP/patch/report exports, archive guards, request limits and offline regression coverage. The project previously existed as a simpler single-file suggestion prototype. Describe these changes honestly in the submission if required by the submission period.

Licensed under MIT. See LICENSE.
