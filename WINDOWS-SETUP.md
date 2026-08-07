# Factory Worker — Windows (native) quickstart

Run the local worker on a Windows machine (e.g. i7 + RTX 3060). The worker claims
jobs from Supabase and runs them with **`claude -p`** using **this machine's own
Claude Code subscription** — no Anthropic API key. Video encoding is offloaded to
the **RTX GPU (NVENC)** automatically.

The order is exactly what you asked for: **install prerequisites → sign in to
Claude once → the worker autostarts at logon.**

---

## 1. Install the four prerequisites

Open **PowerShell** and install what's missing:

```powershell
# Claude Code CLI (native Windows installer) — then sign in later in step 3
winget install Anthropic.ClaudeCode

# Python 3.11+  (tick "Add to PATH" if using the python.org installer)
winget install Python.Python.3.12

# Git (to clone the repo)
winget install Git.Git

# ffmpeg WITH NVENC — the gyan.dev "full" build includes h264_nvenc
winget install Gyan.FFmpeg
```

> Also required for the GPU: an up-to-date **NVIDIA driver** (GeForce Experience
> or nvidia.com). `nvidia-smi` should work in a terminal.
> **Google Chrome** is only needed for jobs that drive a real browser (e.g. Suno).

Close and reopen PowerShell so the new PATH entries take effect.

## 2. Clone and install

```powershell
git clone <your-repo-url> Ai-youtube-pipeline
cd Ai-youtube-pipeline
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

`install.ps1` checks the `claude` CLI, installs Python deps, runs the **GPU
preflight**, creates `secrets\factory.env` + `.env` from templates, dry-runs the
worker, and offers to register a **Scheduled Task that starts the worker at every
logon**. Say **y** to that.

## 3. Sign in to Claude (once)

The worker runs jobs **as you**, so authenticate Claude Code once:

```powershell
claude
```

Complete the browser login, then type `/exit`. The subscription token is cached,
so you won't need to repeat this on every boot.

## 4. Fill in Supabase settings

Edit **`secrets\factory.env`** (Notepad is fine):

```ini
SUPABASE_URL=https://YOUR-PROJECT-ref.supabase.co
SUPABASE_SERVICE_KEY=<service_role key from Supabase → Settings → API>
```

To join the **existing** factory, use that project's URL + service_role key. For
a fresh project, apply `supabase\migrations\*.sql` with the Supabase CLI first.

The GPU knobs are already pre-filled for the RTX 3060 (`FACTORY_FFMPEG_HWACCEL=auto`,
`FACTORY_REMOTION_GL=angle`, `FACTORY_REMOTION_CONCURRENCY=8`). Keep
`FACTORY_MAX_PARALLEL=2` on a 16 GB machine.

## 5. Start it

```powershell
Start-ScheduledTask -TaskName FactoryWorker      # starts now; also auto-starts at logon
Get-Content logs\factory_worker.log -Wait        # watch it work
```

Or run it in the foreground (keeps itself alive if it crashes):

```powershell
powershell -ExecutionPolicy Bypass -File deploy\run-worker.ps1
```

That's it — the worker is live and pulling jobs.

---

## Verify the GPU is doing the encoding

```powershell
python scripts\gpu_check.py
```

Prints your driver, confirms ffmpeg has `h264_nvenc`, runs a live test-encode, and
shows a **libx264-vs-NVENC benchmark** (typically several × faster on the 3060).
Exit code 0 means the worker will use the GPU automatically.

If it reports `h264_nvenc not in this ffmpeg build`, your ffmpeg lacks NVENC —
install `Gyan.FFmpeg` (above) or a full build from https://ffmpeg.org, and make
sure that ffmpeg is first on PATH (or set `FACTORY_FFMPEG` in `secrets\factory.env`).

**Honest scope:** the GPU accelerates the video *encode/render* stage only. It
does not speed up `claude -p` reasoning or the Leonardo / Suno / ElevenLabs /
HeyGen cloud calls — those are network-bound and dominate many jobs.

## Managing the worker

| Action | Command |
|---|---|
| Start now | `Start-ScheduledTask -TaskName FactoryWorker` |
| Stop | `Stop-ScheduledTask -TaskName FactoryWorker` |
| Remove autostart | `Unregister-ScheduledTask -TaskName FactoryWorker -Confirm:$false` |
| Live logs | `Get-Content logs\factory_worker.log -Wait` |
| One test claim | `$env:FACTORY_REPO=$PWD; python scripts\factory_worker.py --once` |
| Pause claims (no restart) | in Supabase set `factory_settings.worker_paused = '1'` (`'0'` resumes) |

## Notes & gotchas

- **Autostart runs in your interactive session** (not a background service) on
  purpose — that's what gives `claude` your subscription auth and lets
  Chrome-driving jobs reach a real browser. It starts hidden at logon.
- **npm-installed `claude`** is a `.cmd` shim; the worker already wraps it in
  `cmd /c` so it launches correctly. The native `claude.exe` also works.
- **Memory:** 16 GB is tight. Keep `FACTORY_MAX_PARALLEL=2` and avoid a third
  heavy job while Chrome is open, or you'll hit swap.
- **Job cancellation** on Windows uses `taskkill /T` to stop the whole job tree
  (claude + ffmpeg) — handled by the worker, nothing to configure.
