# bc02 AVD shoot — 2026-08-16 (VJ directive: real app, preflight everything)

Story: Ch.1 secretly built on Haiku (cheapest) → Ch.2 = MODEL + EFFORT dial → Opus 5 polish.

## Tapes (native 1080x2400, dark theme, demo statusbar, no real name on screen)
- appM1.mp4 (72.6s) — THE DIAL: model sheet opens showing Haiku 4.5 checked + "Extended" toggle
  (cheap mode visual) → tap Opus 5 → reopen → Effort → High. Then crisp prompt typed live
  (marks: sheet 7.4 / opus 14.3 / effort 23-27 / typing 37.8-47.1 / attach 54.7-70.9 / SENT 76.8
  — subtract rec_appM1_t0=4.2 for in-tape times) + Files-tab attach of yesterday's index.html.
- appM2.mp4 (17.8s) — Opus thinking chips + Q1 arrives ("real WhatsApp number — every Order
  button is dead" = the money question).
- appM4/5/6.mp4 (~175s each) — generation: "Building now — the answer box reads its facts
  straight out of the page's own markup", "Creating index.html" artifact card, then the
  4-bugs-fixed self-test text ("'dinner' was matching the lunch rule… 'Sunday open hai?' ranked
  wrong"), artifact full-preview (premium dark-green site), ⋮ menu → Download on camera.
- appB_ask2.mp4 (21.4s) — MONEY SHOT on live anitas-tiffin.netlify.app in AVD Chrome:
  tap chip "Sunday open hai?" → Hinglish answer, live-aware ("Aaj Sunday hai, kitchen band
  hai") → tap "UPI chalega?" → "UPI ya cash — dono chalta hai. UPI ID anitas.tiffin@upi".
- Q&A answer typing (A1-A3) NOT on tape (Gboard floating-bar defect) — stills exist:
  scratchpad q1/q2/q3.png. Cut plan: summarize Q&A in one beat over appM2 + stills.

## Story stats (verified)
- Haiku file 8.4KB → Opus file 44.9KB (5.3x)
- Opus asked exactly 3 questions: dead WhatsApp button, missing delivery/payment/plans info,
  pure-veg/Jain + FSSAI ("rather leave it out than fake it")
- Opus self-tested and fixed 4 bugs before handing over
- Everything wired to ONE CONFIG constant ("change it in exactly one place before launch")

## Deployed
- site_opus/index.html LIVE at anitas-tiffin.netlify.app (netlify site id 665d5de5-…, --prod)

## Gotchas for next AVD shoot (also in memory)
- Gboard floating toolbar appears whenever `adb input text` fires (hardware-kb mode);
  `show_ime_with_hard_keyboard` 0 CAUSES the pill; force-stop Gboard clears until next input.
  CHIP TAPS instead of typing whenever the page offers them.
- screenrecord to /data/local/tmp/ (NOT /sdcard) — media-indexed recordings appear in the
  Files picker on camera.
- File picker: index.html lives under Documents tab, not Recents.
- A blind KEYCODE_BACK from a fresh chat exits the app. Never tap without a dump-verified target.
- Claude app: artifact ⋮ menu = Preview/Code/Publish/Copy/Download.
