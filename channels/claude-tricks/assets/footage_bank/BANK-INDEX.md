# AI Unpacked — footage bank (`assets/footage_bank/`)

Real `record_demo.py --followup` tapes kept OUT of any single episode's asset folder so a
future short can cut one without re-recording. **Read this before recording a new session:**
a bank job that films a demo already sitting here is pure waste, and the second tape is never
identical, so it also splits the evidence for one lesson across two files.

Every entry is a fail -> fix -> proof session in ONE chat, both halves gated on the filmed
text (`--fail-terms` / `--fix-forbid-terms` / `--fix-seed-terms`); the sidecar beside each mp4
carries the measured beat times an episode's in-points must come from.

| session | dur | the fix it proves | gates that passed on camera | used by |
|---|---|---|---|---|
| `session_a_format_fix` | 44.233s | asking for a format, not just a topic | fix-forbid: clean | unused |
| `session_b_prompt_structure` | 64.633s | structuring the prompt instead of piling on words | fix-forbid: clean | unused |
| `session_c_task_overload` | 45.967s | one task per ask instead of five at once | fix-forbid: clean | unused |
| `session_d_document_grounding` | 83.433s | pasting the actual document instead of describing it | fail: `depends`, `often`, `usually`; fix-seed: `Reinstatement Levy`, `Schedule C` | **build 30** (shipped as `assets/ep30/raw_doc.mp4`) |

**Source:** `chatgpt.com` logged OUT (`--no-profile --dark`). Two consequences worth knowing
before planning a beat on any of these: the frame carries **Log in / Sign up for free** chrome
(fine for a prompting lesson, fatal for a memory/personalization lesson — playbook §10b), and
the anonymous file inputs are **image-only**, so a document can only ever be *pasted*
(`--followup-paste`), never attached (measured 2026-08-06, all three inputs reject a .txt).

_Last updated 2026-08-06._
