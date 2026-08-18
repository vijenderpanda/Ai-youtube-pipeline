#!/bin/bash
# Wrapper for the Aashiqana TEST 1 RELATED_VIDEO read (launchd-invoked).
cd /Users/vijenderpanda/Ai-youtube-pipeline
/Users/vijenderpanda/miniconda3/bin/python3 scripts/test1_read.py --label "${1:-read}" >> /tmp/test1_read.log 2>&1
