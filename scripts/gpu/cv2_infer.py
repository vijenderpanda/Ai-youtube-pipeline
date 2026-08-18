#!/usr/bin/env python3
"""CosyVoice 2 English zero-shot inference (run by the CosyVoice venv python on the
worker). Loads a reference wav + its transcript, synthesizes --text, writes --out.
Prints CV2_INFER_OK <path> on success."""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv-repo", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--ref-text", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fp16", default="0")
    a = ap.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")
    # Matcha-TTS submodule + repo root must be importable; run from the repo root.
    sys.path.insert(0, os.path.join(a.cv_repo, "third_party", "Matcha-TTS"))
    sys.path.insert(0, a.cv_repo)
    os.chdir(a.cv_repo)

    import torch
    import torchaudio
    from cosyvoice.cli.cosyvoice import CosyVoice2
    from cosyvoice.utils.file_utils import load_wav

    cv = CosyVoice2(a.model_dir, load_jit=False, load_trt=False,
                    fp16=(a.fp16 == "1"))
    prompt = load_wav(a.ref, 16000)
    chunks = [o["tts_speech"] for o in
              cv.inference_zero_shot(a.text, a.ref_text, prompt, stream=False)]
    if not chunks:
        print("CV2_INFER_FAIL no audio produced")
        sys.exit(1)
    audio = torch.cat(chunks, dim=1) if len(chunks) > 1 else chunks[0]
    torchaudio.save(a.out, audio, cv.sample_rate)
    print("CV2_INFER_OK", a.out, "sr", cv.sample_rate)


if __name__ == "__main__":
    main()
