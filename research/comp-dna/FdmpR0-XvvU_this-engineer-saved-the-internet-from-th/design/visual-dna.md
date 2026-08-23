## Archetype
"Talking-head narrator + generative data-graphic explainer" — host bookends the story (hook, close) while the middle is almost entirely abstract dark-mode motion graphics (radar sweeps, node networks, terminal logs, counters) standing in for the technical narrative, punctuated by real proof screenshots (news article, code, phone article).

## Hook mechanic (first 3s)
Host full-frame delivers the headline as kinetic on-screen text ("This Person Saved the internet from the Worst cyber attack") while a red branded bumper/sting graphic (looks like a stylized red hand/logo) flashes over him. Curiosity-gap title + immediate visual pattern-interrupt in under 1s, no slow build.

## Caption grammar
Bottom-third, 2-4 words per burst, lowercase, bold white sans, word-by-word reveal timed to speech. No stroke/outline — relies on near-black background for contrast. Occasional word gets accent-color emphasis. Captions are the ONLY text during b-roll/graphic segments — headline text at top is separate and rarer (used for section-opening statements, not every line).

## Information density
Very high — a new visual element (graphic swap, counter tick, screenshot, log line) roughly every 1-1.5s even when the underlying camera shot hasn't cut. Numbers/stats appear constantly (percentages, machine counts, dollar-like ticking counters) to manufacture precision and momentum even where the actual figures are illustrative.

## Reusable asset components
- **Terminal boot/log typewriter** — monospace green-on-black lines typing themselves (`[OK] Booting system...`), used for "something technical is happening" beats
- **Radar/sonar sweep with % readout** — circular scanning graphic with a rotating sweep line + live percentage, used for "detecting/analyzing" beats
- **Node-network graph** — dots connected by thin lines, zooms/pans, used for "spreading/scale" beats; nodes turn red when "compromised"
- **Scale-shock counter** — large number that ticks upward rapidly (e.g. 17,107 → 11,509,337), used to sell magnitude in ~1-2s bursts
- **Proof screenshot frame** — real news article or phone-UI mockup, slow zoom/pan into a highlighted quote, used as a credibility anchor
- **Character card** — small photo + name/title pill overlay (e.g. "Andres Freund / Microsoft Engineering"), introduces a real person as a "character"
- **Fake code editor** — syntax-colored code block overlay (Python snippet), used as a generic "this is technical/real" prop, not literal to the actual exploit
- **Compromise grid** — small red/white square grid filling in over time, visualizes "how many/how close to total compromise" at a glance
- **Danger lock icon** — simple red padlock/target icon that appears at threat-escalation beats (private key, full access)
- **Red bumper/sting** — recurring branded graphic flash used at open and close to bookend the story

## Colors → content mapping notes
- Near-black bg (#0A0C0F) is constant — nothing ever goes to a light background except the proof screenshots (article/phone), which stay their native white/newsprint color for authenticity.
- Green (#2ED9A0-ish, terminal/matrix green) = code, logs, "the system working as normal" or "hacker doing technical work."
- Red (#E4382E) = danger, compromise, alerts, the sting bumper, and the host's background hand-print graphic — ties host identity to the "danger/thriller" register.
- White text/graphics = neutral narration and captions.

## Weaknesses / what NOT to copy
- Numbers (0.5s delay, ticking counters, percentages) look precise but are likely dramatized/approximate — don't imply false rigor if the source data isn't real.
- The "fake code editor" Python snippet (csv import) has nothing to do with the actual XZ Utils/SSH exploit — it's a generic technical prop, not accurate; don't let illustrative code stand in for something that needs technical accuracy in a more expert-facing channel.
- Density is extremely high (near-constant graphic swap) — for a slower/more premium brand this reads as noisy/anxious; would need throttling for calmer channels.
- Long paragraph-of-text b-roll shots (dense article scans) are mostly illegible at speed — they work as "texture/credibility flash" only, not as actual readable content; don't rely on viewers reading them.
