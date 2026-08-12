#!/usr/bin/env python3
"""Poller: download Ep02 Seedance clips as they complete; exit when folder has >=6 mp4s or timeout."""
import json, re, urllib.request, subprocess, os, time
REPO="/Users/vijenderpanda/Ai-youtube-pipeline"
OUT=os.path.join(REPO,"channels/already-happening/assets/ep02/motion"); os.makedirs(OUT,exist_ok=True)
KEY=re.search(r"LEONARDO_API_KEY=(\S+)",open(os.path.join(REPO,".env")).read()).group(1)
H={"Authorization":f"Bearer {KEY}","Accept":"application/json"}
MARK=["holographic AI interface","translucent screen","open-plan office","workflow panels","near-empty futuristic","APPROVE button"]
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=H)))
uid=get("https://cloud.leonardo.ai/api/rest/v1/me")["user_details"][0]["user"]["id"]
def count(): return len([f for f in os.listdir(OUT) if f.endswith('.mp4')])
for _ in range(60):                       # ~60 * 20s = 20 min
    try: gens=get(f"https://cloud.leonardo.ai/api/rest/v1/generations/user/{uid}?offset=0&limit=10")["generations"]
    except Exception: time.sleep(20); continue
    for g in gens:
        p=g.get("prompt") or ""
        if not any(m in p for m in MARK): continue
        m=re.findall(r'https?://[^"\\ ]+?\.mp4',json.dumps(g))
        if not m: continue
        head=re.sub(r"[^a-z0-9]+","-",p[:34].lower()).strip("-")
        path=os.path.join(OUT,f"{head[:30]}_{g['id'][:8]}.mp4")
        if not os.path.exists(path):
            subprocess.run(["curl","-sL",m[0],"-o",path],check=False); print("saved",os.path.basename(path),flush=True)
    if count()>=6: print("DONE",count()); break
    time.sleep(20)
print("poller exit; clips:",count())
