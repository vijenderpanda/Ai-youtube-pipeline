"""Premium shorts caption render layer — Python -> Remotion bridge.

Replaces the old ffmpeg "burn subtitles" step. The AI steps (yt-dlp, Whisper,
clip selection) are untouched: Whisper's word-level timestamps ARE the caption
input. See shorts-premium-render-CONTEXT.md (this repo) for the full design.

Data contract (Python -> Remotion), written to render/props.json:
    {
      "videoSrc": "input.mp4",
      "captions": [{"text": "premium", "startMs": 540, "endMs": 1180}, ...],
      "style": "tier2",
      "handle": "@yourchannel",
      "durationInFrames": 300
    }
"""

import json
import shutil
import subprocess
from pathlib import Path

RENDER_DIR = Path(__file__).parent / "render"
PUBLIC = RENDER_DIR / "public"


def _npx() -> str:
    # Windows ships npx.cmd; resolve it so shell=False works.
    return shutil.which("npx.cmd") or shutil.which("npx") or "npx"


def whisper_to_words(whisper_result: dict) -> list[dict]:
    """Convert a Whisper result (with word_timestamps=True) into the caption
    contract: one entry per word, milliseconds."""
    return [
        {
            "text": w["word"].strip(),
            "startMs": int(w["start"] * 1000),
            "endMs": int(w["end"] * 1000),
        }
        for seg in whisper_result.get("segments", [])
        for w in seg.get("words", [])
    ]


def render_short(
    clip_path: str,
    words: list[dict],
    out_path: str,
    style: str = "tier2",
    handle: str = "@yourchannel",
    fps: int = 30,
    duration_s: float | None = None,
) -> str:
    """Render a premium captioned short.

    words: [{"text": str, "startMs": int, "endMs": int}, ...]  # per word, from Whisper
    duration_s: total output length. Pass the SOURCE CLIP duration so a trailing
        no-caption tail isn't truncated. Defaults to the last caption's end time.
    Returns out_path.
    """
    PUBLIC.mkdir(parents=True, exist_ok=True)
    shutil.copy(clip_path, PUBLIC / "input.mp4")

    if duration_s is None:
        duration_s = words[-1]["endMs"] / 1000 if words else 5
    props = {
        "videoSrc": "input.mp4",
        "captions": words,
        "style": style,
        "handle": handle,
        "fps": fps,
        "durationInFrames": max(1, round(duration_s * fps)),
    }

    props_path = RENDER_DIR / "props.json"
    # UTF-8, NO BOM — utf-8-sig breaks Remotion's JSON parse. Keep encoding="utf-8".
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        _npx(),
        "remotion",
        "render",
        "src/index.ts",
        "Short",
        str(out),
        f"--props={props_path}",
        "--concurrency=2",
    ]
    # shell=False + resolved npx path so PowerShell/cmd quoting never touches props.
    subprocess.run(cmd, cwd=str(RENDER_DIR), check=True, shell=False)
    return out_path


if __name__ == "__main__":
    # Smoke test: render render/public/input.mp4 with three demo words.
    demo_words = [
        {"text": "this", "startMs": 0, "endMs": 320},
        {"text": "is", "startMs": 320, "endMs": 540},
        {"text": "premium", "startMs": 540, "endMs": 1180},
    ]
    render_short(
        str(PUBLIC / "input.mp4"),
        demo_words,
        str(RENDER_DIR / "out" / "demo.mp4"),
    )
