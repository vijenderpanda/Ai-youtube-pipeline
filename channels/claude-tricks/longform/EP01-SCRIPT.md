# LONG-FORM EP01 — "I Shipped an iPhone App in 3 Hours" (~15 min)

Status: DRAFT v1 (2026-08-25). Storyboard v3 APPROVED (option-A cold open).
Voice: ELEVEN_VOICE Hrithik `ZZ5OIPIzxVJswEhc0UXt`, style 0.4, breaks 0.4s. PURE ENGLISH.
Identity: champagne editorial. Host stills: `host_library/longform_champagne_v1` picks.

## HONESTY GATES (block render, not script)
- [ ] A1 listing: swap mock chrome for a REAL App Store/TestFlight capture. If the app is
      not publicly live at render time, VO says "submitted to Apple", never "live".
- [ ] A2 timestamps: pull the REAL prompt-sent + submit times from the missnomeetings
      session log; re-voice if not 3:04/6:12/3h08.
- [ ] Ch2 build tape: re-capture a real Claude Code build replay (current tape is the
      phone-connection check only).
- [ ] Ch4: App Store Connect submission capture needed from VJ (or screen-record replay).

## COLD OPEN (0:00–0:45)
A1 (listing, 2s silent, then):
> That's a real app. On the real App Store.
A2 (timestamp card):
> Now look at the timestamps. Prompt sent, three oh four in the afternoon. Submitted to
> Apple, six twelve. Three hours and eight minutes.
A3 (host wide):
> By the end of this video you'll know every step. Because I'm going to show you all of
> it. Including the parts that broke.
PROMISE (tape punch-in, phone):
> One afternoon. One tool. Zero lines of code written by me. This is the app it built.

## CH1 — THE IDEA (1:20–3:00) [card sting, then screen+pip]
> MissNoMeetings started as a personal problem. My phone buries meeting invites, and I
> kept missing calls. Not because I was busy. Because the reminder fired on my laptop,
> in another room.
> So I did not open a design tool. I did not write a spec document. I opened Claude Code
> and typed one paragraph. What the app should do, who it is for, and the one rule that
> mattered: the alarm rings on the phone, loudly, even when the app is closed.
> That paragraph is the entire product brief. You will see the exact text at the end —
> copy it, change one line, and it becomes your app.

## CH2 — THE BUILD (3:00–6:00) [punch-ins on Claude Code; pop "3 HOURS" at 5:30]
> Watch what happens to that paragraph. It plans the project. It creates the Xcode
> files. Swift, which I do not write. The timer logic, the alarm scheduling, the
> permissions — each one appears, compiles, and gets fixed when it breaks.
> And things DID break. The first build failed on a signing profile. I pasted the error
> back. It read it, fixed the project settings, and moved on. That loop — build, fail,
> paste, fix — is the whole skill. There is no step where I write code.

## CH3 — ON MY IPHONE (6:00–8:30) [simulator punch-in, then device]
> First run in the simulator. The meeting list is real, the timer counts, the alert
> fires. But a simulator proves nothing about the thing that mattered — the alarm on a
> locked phone. So, real device.
> This part every tutorial skips: Developer Mode, the trust dialog, the cable dance.
> It rejected my phone twice. Here is exactly what fixed it.

## MID-ROLL (8:30–9:00) [host medium]
> Why is this suddenly possible? One word: agents. The model does not suggest code any
> more. It builds, runs the build, reads its own errors, and repairs them. Your job
> shrinks to two things — describing what you want, and testing whether you got it.

## CH4 — THE APP STORE (9:00–12:30) [B-roll profile beat 9:05, then submit tape;
pop "APPROVED" at 12:30]
> Signing. Archive. App Store Connect. Screenshots, privacy questions, export
> compliance. The boring wall between "it works on my phone" and "anyone can install
> it". We go through every screen, because this is the part nobody shows.
> Total time from the first prompt to pressing Submit: three hours and eight minutes.

## PAYOFF (13:00–14:30) [exact prompt on screen, highlighted]
> Here is the exact prompt I started from. Pause and copy it. The structure is what
> matters: the problem, the user, and one non-negotiable rule. Change those three
> things and this becomes your app instead of mine.

## OUTRO (14:30–15:15) [host close]
> If a meetings app takes an afternoon, ask what else does. Next video: I cancel my
> entire paid creator stack and replace it with free AI, one tool at a time. Subscribe
> so you are there when it ships.

## TEST SLICE (approved scope: 0:00–~2:00)
Beats: A1 → A2 → A3 → PROMISE → CH1 card → CH1 first paragraph.
Builder: `ep1_testslice.py`. 1080p only. No arm, no upload.
