# Patchwork demo and submission notes

## Three-minute video outline
0:00–0:25 — Introduce the audience and problem: a developer encounters an unfamiliar bug and needs a focused repair with enough context to review it.
0:25–0:45 — Open Studio, load Fractional averages, show the bug and the existing test selected as context.
0:45–1:30 — Generate a live repair. Show NVIDIA Nemotron's exact model ID, token usage, diagnosis, changes and diff.
1:30–2:05 — Explain the evidence: syntax checks actually ran; suggested tests did not. Inspect a risk and a proposed regression test.
2:05–2:35 — Accept into the workspace; download the workspace ZIP, unified patch and review report. Show that the supporting test file is preserved in the supported-text export.
2:35–3:00 — Summarise the intended benefit and limits. The app uses Nebius Token Factory for inference and keeps the human review decision explicit.

Do not record credentials. Do not claim test execution, benchmark scores, user adoption or measured time savings without evidence.

## Evidence for the judging criteria
- Technological implementation: real model request, selected source context, typed response checks, real parser evidence, portable artifacts and offline regression coverage.
- Design: landing-to-studio onboarding, example projects, file search, source editing, progress/error states, review tabs, keyboard support, responsive layout and decision handling.
- Potential impact: demonstrate one specific debugging task for a small-project developer. Collect user feedback and measure task completion time before making impact claims.
- Quality of the idea: a review package that carries the diagnosis, source change, actual check results, suggested tests and decision together.

## Still needed before submission
- Confirm the new deployment and one live inference request.
- Watch the full demo at desktop and mobile widths; verify downloads in a real browser.
- Public YouTube video of at most three minutes.
- Devpost description, selected track, public demo and repository URLs.
- First-hand feedback on Token Factory and NVIDIA tools. Record specific successes or failures encountered during live use.
- Check the official rules and submission dates. Include the prior-project/update explanation where required.
- If entered into Coding and Agentic Engineering, revisit its execution/testing requirements. The current app does not execute model-generated code.

## Feedback worksheet
Record the model ID, date, input size, tokens, latency, expected result, actual result and any retry. Record an actual provider problem only after observing it. Keep raw secrets and proprietary source out of feedback.
