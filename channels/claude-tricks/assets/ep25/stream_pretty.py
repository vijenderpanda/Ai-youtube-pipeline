#!/usr/bin/env python3
"""Ep25 on-camera renderer: stdin = `claude -p --output-format stream-json` lines,
stdout = the EXACT human lines the factory worker prints in the dashboard log.

render_line() is IMPORTED from scripts/factory_worker.py -- not reimplemented --
so what the tape films is literally the worker's renderer. FACTORY_REPO is
exported in the tape's hidden setup block (never shown on camera).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.environ["FACTORY_REPO"], "scripts"))
from factory_worker import render_line  # noqa: E402  the worker's own renderer

for raw in sys.stdin:
    line = render_line(raw)
    if line:
        print(line, flush=True)
