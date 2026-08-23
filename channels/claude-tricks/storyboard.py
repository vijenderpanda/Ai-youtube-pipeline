#!/usr/bin/env python3
"""storyboard.py — the owner gate's artifact (docs/MOTION-PIPELINE.md, stage 5).

Renders REAL Remotion stills off the FILM MANIFEST on the planned clock and
composes the one-page approval sheet: per-beat frames, the knee and payoff
marked at their seconds, the mute table (what a muted viewer sees, per line),
the carry element, the give, and the asset list with cost. NOTHING else renders
and nothing paid runs before the owner's yes on this page — VO deliberately
comes after, so line edits at review are free.

The stills are the actual component with the actual resolved props — a
storyboard of drawings can lie about what the build will do; this one cannot.

Usage:
  python3 channels/claude-tricks/storyboard.py films/forgets.manifest.json
  -> channels/claude-tricks/films/<ep>.storyboard.html (stills embedded)
"""
import argparse
import base64
import html as H
import json
import os
import subprocess
import sys
import tempfile

CH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(CH))
STUDIO = os.path.join(ROOT, "remotion-studio")
FPS = 30

sys.path.insert(0, CH)
from cast_scenes import planned_clock, resolve, validate  # noqa: E402


def resolve_props(obj, bounds):
    if isinstance(obj, str) and obj.startswith("@beat"):
        return round(resolve(obj, bounds), 3)
    if isinstance(obj, dict):
        return {k: resolve_props(v, bounds) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_props(v, bounds) for v in obj]
    return obj


def still(comp, props_path, t, out, scale=0.35):
    subprocess.run(
        ["npx", "remotion", "still", comp, out,
         f"--props={props_path}", f"--frame={int(round(t * FPS))}",
         f"--scale={scale}", "--log=error"],
        cwd=STUDIO, check=True)


def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    a = ap.parse_args()
    mp = a.manifest if os.path.isabs(a.manifest) else os.path.join(CH, a.manifest)
    man = json.load(open(mp))

    errs, warns, bounds = validate(man)
    if errs:
        for e in errs:
            print(f"!! {e}")
        sys.exit(1)
    total = bounds[-1]

    # the primary spine component: first entry in manifest.spine
    spine = man["spine"][0]
    props = resolve_props(man["cookbook"][spine], bounds)
    kt = resolve(man["knee"]["anchor"], bounds)
    pt = resolve(man["payoff"]["anchor"], bounds)

    tmp = tempfile.mkdtemp(prefix="sb_")
    pj = os.path.join(tmp, "props.json")
    json.dump(props, open(pj, "w"))

    # one still per line (at its visual midpoint) + the knee + the payoff
    shots = []
    for i, ln in enumerate(man["lines"]):
        mid = (bounds[i] + bounds[i + 1]) / 2
        shots.append((f"beat {i}", mid, ln))
    shots.append(("THE KNEE", kt + 0.05, None))
    shots.append(("THE PAYOFF", pt + 0.15, None))
    shots.sort(key=lambda s: s[1])

    comp = f"{spine}Film"
    cards = []
    for label, t, ln in shots:
        out = os.path.join(tmp, f"f{int(t*100):05d}.png")
        print(f">> still {label} @ {t:.2f}s")
        still(comp, pj, t, out)
        special = ln is None
        cap = (f"<p class='mute'><span>MUTED VIEWER SEES</span>"
               f"{H.escape(ln['subject'])}: {H.escape(ln['from'])} → <b>{H.escape(ln['to'])}</b></p>"
               f"<p class='vo'><span>VO</span>{H.escape(ln['vo'])}</p>") if ln else \
              (f"<p class='mute'><span>{'U9 — 4-8s WINDOW' if 'KNEE' in label else 'U8 — ≥75% OF RUNTIME'}</span>"
               f"{H.escape(man['knee']['what'] if 'KNEE' in label else man['payoff']['what'])}</p>")
        cards.append(f"""<figure class="fr{' key' if special else ''}">
<div class="fh"><b>{H.escape(label)}</b><span>{t:.2f}s</span></div>
<img src="data:image/png;base64,{b64(out)}" alt="{H.escape(label)}">
<figcaption>{cap}</figcaption></figure>""")

    give = man["give"]["prompt"]
    page = f"""<title>{H.escape(man['title_candidates'][0])} — Storyboard</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#08080D;--panel:#14151D;--edge:#242634;--paper:#F4F4FA;--mute:#8A8CA2;--mag:#FF2E9A;--cyan:#2DE0F5;--amber:#FFB443;--good:#3ECF8E}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--paper);font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1200px;margin:0 auto;padding:48px 24px 90px}}
.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.22em;text-transform:uppercase;color:var(--mag);margin:0 0 12px}}
h1{{font-family:Anton,sans-serif;font-weight:400;font-size:clamp(34px,5.4vw,58px);line-height:.96;margin:0 0 14px;text-wrap:balance}}
.sub{{color:var(--mute);font-size:15px;line-height:1.62;max-width:64ch;margin:0}}
.sub b{{color:var(--paper);font-weight:500}}
.bar{{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 0;padding:12px 0 20px;border-bottom:1px solid var(--edge)}}
.tag{{font-family:"IBM Plex Mono",monospace;font-size:11px;border:1px solid var(--edge);border-radius:99px;padding:6px 12px;color:var(--mute);background:var(--panel)}}
.tag b{{color:var(--paper);font-weight:500}}
h2{{font-family:Anton,sans-serif;font-weight:400;font-size:25px;margin:48px 0 8px}}
.lede{{color:var(--mute);font-size:14px;line-height:1.64;max-width:74ch;margin:0 0 16px}}
.lede b{{color:var(--paper);font-weight:500}}
.frames{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px;margin-top:20px}}
.fr{{background:var(--panel);border:1px solid var(--edge);border-radius:15px;overflow:hidden}}
.fr.key{{border-color:rgba(255,46,154,.6);box-shadow:0 18px 50px -30px rgba(255,46,154,.8)}}
.fh{{display:flex;justify-content:space-between;padding:11px 14px 9px;border-bottom:1px solid var(--edge)}}
.fh b{{font-family:Anton,sans-serif;font-weight:400;font-size:13px;letter-spacing:.04em}}
.fh span{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--cyan)}}
.fr img{{width:100%;display:block;background:#000}}
figcaption{{padding:12px 14px 14px}}
.mute{{font-size:12.3px;color:var(--paper);line-height:1.55;margin:0 0 9px}}
.mute span,.vo span{{display:block;font-family:"IBM Plex Mono",monospace;font-size:8.5px;letter-spacing:.16em;color:var(--cyan);margin-bottom:3px}}
.vo{{font-size:12px;color:var(--mute);border-left:2px solid var(--mag);padding-left:10px;margin:0}}
.vo span{{color:var(--mag)}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px;margin-top:16px}}
.card{{background:var(--panel);border:1px solid var(--edge);border-radius:14px;padding:16px 18px}}
.card h4{{font-size:13px;margin:0 0 8px;font-weight:600}}
.card h4 em{{font-style:normal;display:block;font-family:"IBM Plex Mono",monospace;font-size:9.5px;letter-spacing:.13em;color:var(--amber);margin-bottom:5px;text-transform:uppercase}}
.card p{{color:var(--mute);font-size:12.5px;line-height:1.6;margin:0 0 8px}}
.card p:last-child{{margin:0}}.card b{{color:var(--paper);font-weight:500}}
code{{font-family:"IBM Plex Mono",monospace;font-size:.9em;color:var(--cyan)}}
.prompt{{background:var(--panel);border:1px solid rgba(255,46,154,.4);border-radius:14px;padding:18px 20px;margin-top:14px;font-family:"IBM Plex Mono",monospace;font-size:13px;line-height:1.7;color:var(--paper)}}
.foot{{margin-top:48px;padding-top:18px;border-top:1px solid var(--edge);color:var(--mute);font-size:12.3px;line-height:1.7}}
</style>
<div class="wrap">
<p class="eyebrow">AI Unpacked · motion pipeline · pilot · <b style="color:var(--amber)">for approval — nothing rendered, no VO spent</b></p>
<h1>{H.escape(man['title_candidates'][0])}</h1>
<p class="sub">These are <b>real frames from the real component with the real resolved props</b> on the
planned clock — a drawn storyboard can lie about what the build will do; this one cannot. VO is
deliberately unsynthesized: a line edit at this review costs nothing.</p>
<div class="bar">
<span class="tag">class <b>{H.escape(man['class'])}</b></span>
<span class="tag">honesty <b>{H.escape(man['honesty'])}</b></span>
<span class="tag">planned <b>{total:.1f}s body</b></span>
<span class="tag">knee <b>{kt:.1f}s</b></span>
<span class="tag">payoff <b>{pt:.1f}s = {pt/total:.0%}</b></span>
<span class="tag">cost to build <b>~$1 (VO only)</b></span>
</div>

<h2>The carry</h2>
<p class="lede">{H.escape(man['carry'])}</p>

<h2>Every beat, as the muted viewer sees it</h2>
<div class="frames">{''.join(cards)}</div>

<h2>The give — indexed, above the fold, pinned</h2>
<div class="prompt">{H.escape(give)}</div>

<h2>Title + assets</h2>
<div class="grid2">
<div class="card"><h4><em>title candidates</em>{H.escape(man['title_candidates'][0])}</h4>
<p>{'<br>'.join(H.escape(t) for t in man['title_candidates'][1:]) or '—'}</p>
<p><b>The noun-specificity rule applies</b> — settled at arm time, per standing.</p></div>
<div class="card"><h4><em>assets</em>All code, zero generation</h4>
<p><b>ContextTube</b> (new, committed) carries all 8 beats on one spine · <b>OutroGlass</b> card via
<code>gen_outro_glass.py</code> · chips grouped from the VO at build · no FLUX, no Leonardo, no Pexels,
no host — <b>the pilot is deliberately all-SVG</b>.</p></div>
<div class="card"><h4><em>after your yes</em>The exact sequence</h4>
<p>VO synth (~$1) → build at preview scale → <code>qc_motion.py</code> gates → your PHONE GATE
(muted, feed size) → your word for 4K → arm. Fail loops return here, not past you.</p></div>
</div>

<p class="foot">Compiled from <code>films/forgets.manifest.json</code> · validated by
<code>cast_scenes.py</code> (mute table complete, knee in window, payoff withheld, zero numbers spoken)
· stills from <code>{H.escape(comp)}</code> on the planned clock.</p>
</div>"""

    out = os.path.join(CH, "films", f"{man['ep'].lstrip('_')}.storyboard.html")
    open(out, "w").write(page)
    print(f">> storyboard: {out} ({os.path.getsize(out)//1024}KB, {len(shots)} stills)")


if __name__ == "__main__":
    main()
