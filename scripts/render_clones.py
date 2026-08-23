#!/usr/bin/env python3
"""Render CloneReel previews for every research/comp-dna/clones/<id>.json.

    python scripts/render_clones.py [--only ID] [--scale 0.5] [--out research/comp-dna/clones/out]

Each spec -> <out>/<id>.mp4 (+ <id>.jpg filmstrip, 1 fps). Props are passed via a
temp JSON file (remotion --props=<file>). Preview scale 0.5 = 540x960.
"""
import argparse, json, subprocess, sys, tempfile, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STUDIO = REPO / "remotion-studio"
CLONES = REPO / "research/comp-dna/clones"

def render(spec: Path, out_dir: Path, scale: float) -> Path:
    d = json.loads(spec.read_text())
    out = out_dir / f"{spec.stem}.mp4"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(d, f); pf = f.name
    cmd = ["npx", "remotion", "render", "src/index.ts", "CloneReel", str(out),
           f"--props={pf}", f"--scale={scale}", "--codec=h264", "--crf=22", "--log=error"]
    r = subprocess.run(cmd, cwd=STUDIO, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"✖ {spec.stem}\n{r.stderr[-1500:]}", file=sys.stderr); return None
    # 1fps filmstrip for QC
    strip = out_dir / f"{spec.stem}.jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-vf", "fps=1,scale=180:-1,tile=10x2", str(strip)])
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only"); ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--out", default=str(CLONES / "out")); a = ap.parse_args()
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    specs = sorted(CLONES.glob("*.json")) if not a.only else [CLONES / f"{a.only}.json"]
    ok = []
    for s in specs:
        p = render(s, out_dir, a.scale)
        if p: ok.append(p); print(f"✔ {p}")
    print(f"{len(ok)}/{len(specs)} rendered -> {out_dir}")

if __name__ == "__main__":
    main()
