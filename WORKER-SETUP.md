# Factory Worker — install on any machine

> **On Windows?** Follow **[WINDOWS-SETUP.md](WINDOWS-SETUP.md)** instead — it has
> a native PowerShell installer (`install.ps1`) and logon autostart. This page
> covers macOS and Linux.

Run the local factory worker on a new Mac or Linux box. The worker claims jobs
from Supabase (`factory_jobs`) and executes them with **`claude -p`**, using
**that machine's own Claude Code subscription** — there is no Anthropic API key
anywhere in the loop.

```
dashboard → Supabase queue (factory_jobs) → THIS WORKER → claude -p → renders → Supabase storage
```

## Prerequisites

| Need | Why |
|---|---|
| **Claude Code CLI**, signed in | The worker shells out to `claude -p`. Install: <https://docs.claude.com/en/docs/claude-code>, then run `claude` once and log in. |
| **Python 3.9+** | Runs `scripts/factory_worker.py`. |
| **Supabase project** | Holds the job queue + `factory-renders` storage bucket. Either reuse the existing project or stand up a fresh one (see below). |
| **Google Chrome** (optional) | Only jobs that drive real Chrome (e.g. Suno flows) need it open. |
| **ffmpeg** (optional) | Only for video-assembly / Remotion jobs. |

> **Docker note:** a container **cannot** reach the macOS Keychain where the
> Claude subscription token lives, so Docker is not the supported path for the
> worker. Install directly on the host with the CLI method below.

## Install

```bash
git clone <your-repo-url> Ai-youtube-pipeline
cd Ai-youtube-pipeline
./install.sh
```

`install.sh` will:
1. verify the `claude` CLI is present,
2. install Python deps from `requirements.txt`,
3. create `secrets/factory.env` and `.env` from templates (never overwrites existing ones),
4. run a `--dry-run` smoke test,
5. optionally install a background service (launchd on macOS, systemd `--user` on Linux).

Run `./install.sh --no-service` to skip the background service and just run it by hand.

## Configure

Edit **`secrets/factory.env`** (created from [`deploy/factory.env.example`](deploy/factory.env.example)):

```ini
SUPABASE_URL=https://YOUR-PROJECT-ref.supabase.co
SUPABASE_SERVICE_KEY=<service_role key from Supabase → Settings → API>
FACTORY_TOKEN=<any long random string; used by helper scripts>
FACTORY_MAX_PARALLEL=2          # concurrent claude jobs; heavy renders stay serial
```

Only `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` are required to claim jobs. The
worker **refuses to start** without the service key.

`.env` (generation API keys — Leonardo/ElevenLabs/HeyGen/stock) is optional and
only needed by the specific jobs that call those services.

### Supabase schema

- **Reusing the existing project:** nothing to do — just point `factory.env` at it.
- **Fresh project:** with the [Supabase CLI](https://supabase.com/docs/guides/local-development)
  installed and `supabase login` done, run the helper:
  ```bash
  deploy/setup-supabase.sh <project-ref>   # links + applies supabase/migrations/*.sql
  ```
  The worker seeds channels/generators/settings rows itself on first start.

## Run

```bash
# foreground (Ctrl-C to stop)
python3 scripts/factory_worker.py

# single claim attempt, then exit — good for verifying connectivity
python3 scripts/factory_worker.py --once

# print the exact claude command for a fake job; execute nothing
python3 scripts/factory_worker.py --dry-run
```

The worker finds the repo automatically from its own location; set
`FACTORY_REPO=/path/to/Ai-youtube-pipeline` to override (the service units do this).

### As a service

**macOS (launchd)** — installed by `install.sh`:
```bash
tail -f logs/factory_worker.log
launchctl kickstart -k gui/$(id -u)/com.factory.worker   # restart
launchctl unload ~/Library/LaunchAgents/com.factory.worker.plist  # stop
```

**Linux (systemd --user)** — installed by `install.sh`:
```bash
journalctl --user -u factory-worker -f
systemctl --user restart factory-worker
sudo loginctl enable-linger "$USER"   # keep running while logged out
```

## GPU acceleration (NVIDIA NVENC)

If the machine has an NVIDIA GPU (e.g. an RTX 3060), the worker offloads **video
encoding** to the GPU's NVENC hardware encoder — the assembly scripts switch from
software `libx264` to `h264_nvenc` automatically. On a long render (e.g. an
hour-long compilation, or a batch of shorts) this is the difference between many
minutes of CPU encode and a fraction of that.

**Honest scope:** the GPU accelerates the *encode/render* stage only. It cannot
speed up `claude -p` reasoning or the Leonardo / Suno / ElevenLabs / HeyGen cloud
calls — those are network-bound and dominate many jobs. The win is real for
assembly- and Remotion-heavy work, not for planning/generation jobs.

**Verify it's active:**
```bash
python3 scripts/gpu_check.py     # driver + ffmpeg + live test-encode + benchmark
```
Exit 0 = NVENC works and will be used automatically.

**Requirements on the worker machine:**
- NVIDIA driver installed (`nvidia-smi` works). On **WSL2** you need a recent
  Windows driver + the WSL CUDA stack; NVENC is reachable through `/dev/dxg`.
- An **ffmpeg build that includes `h264_nvenc`** (most modern static/gyan.dev
  builds do; some distro packages do not). `gpu_check.py` tells you if it's missing.

**Controls** (in `secrets/factory.env`):
| Var | Default | Effect |
|---|---|---|
| `FACTORY_FFMPEG_HWACCEL` | `auto` | `auto` probe-then-use, `force` skip probe, `cpu` disable |
| `FACTORY_FFMPEG` | (PATH) | override the ffmpeg binary (custom NVENC build) |
| `FACTORY_REMOTION_GL` | unset | `angle` = GPU-accelerated Remotion compositing |
| `FACTORY_REMOTION_CONCURRENCY` | unset | parallel frame renderers (set to CPU threads, e.g. `8`) |
| `FACTORY_REMOTION_HWACCEL` | unset | `if-possible` for Remotion's own hardware encode |

`auto` means **no config is required** — drop the worker on the GPU box and it
uses NVENC if it works, CPU if it doesn't. The Remotion knobs are opt-in; the
recommended values for an i7 + RTX 3060 are pre-filled in the env template.

## Tuning & safety

- **`FACTORY_MAX_PARALLEL`** caps concurrent `claude -p` jobs. Heavy jobs
  (Remotion renders, assembly) always run serially regardless. On a **16 GB**
  box (i7 + RTX 3060) keep it at **2** — and never 3 with Chrome open — to avoid
  OOM. NVENC offloads encode to the GPU but frame rendering + `claude -p` still
  live in system RAM.
- **Pause without restarting:** in Supabase set
  `factory_settings.worker_paused = '1'` to stop new claims instantly; `'0'` resumes.
- Changing `FACTORY_MAX_PARALLEL` takes effect on the next worker restart.

## What is / isn't in this repo

Included: all code (`scripts/`, `supabase/`, `webapp/`, per-channel build scripts,
docs, brand bibles). **Excluded** (see `.gitignore`): secrets, generated media
(`*.mp4/*.mp3/*.jpg/…`), `renders_out/`, `node_modules/`, browser profiles, logs.
Media is regenerated per job and stored in Supabase storage — it is never needed
to run the worker.
