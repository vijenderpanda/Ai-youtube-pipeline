# One-time OAuth setup for the YouTube upload API

Do this once (~15 min). After it, `scripts/youtube_upload.py` uploads + schedules every video with **one command** — no browser driving.

## ⚡ Faster: gcloud CLI (preferred for next projects)
`gcloud` is installed. Project + API enablement are fully CLI:
```bash
gcloud projects create lulla-pipeline --name="Lulla Pipeline"
gcloud config set project lulla-pipeline
gcloud services enable youtube.googleapis.com
```
For auth, the CLI-native path is **Application Default Credentials** (skips manual OAuth-client creation in the console):
```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/youtube.upload,https://www.googleapis.com/auth/youtube,openid
```
Then point the script at ADC instead of `client_secret.json` (in `youtube_upload.py`, swap `get_service()` to build creds from `google.auth.default(scopes=SCOPES)`). The one-time browser **consent** is unavoidable (OAuth), but this folds it into one command. If Google rejects the YouTube scopes for ADC, fall back to the console Desktop-client steps below.

---


## Steps (in your Chrome, signed in as vijender.in@gmail.com)
1. **Create a project:** [console.cloud.google.com](https://console.cloud.google.com) → project picker → **New Project** → name `Lulla Pipeline` → Create.
2. **Enable the API:** APIs & Services → **Library** → search **"YouTube Data API v3"** → **Enable**.
3. **OAuth consent screen:** APIs & Services → **OAuth consent screen** → User type **External** → fill app name (`Lulla Pipeline`) + your email → add scopes `.../auth/youtube.upload` and `.../auth/youtube` → add **your email as a Test user** → Save.
   - ⚠️ In **"Testing"** mode a refresh token expires after **7 days**. To avoid re-authing weekly, click **"Publish app"** (you'll get an "unverified app" screen — safe, it's your own app; click *Advanced → continue*).
4. **Create credentials:** APIs & Services → **Credentials** → **Create credentials → OAuth client ID** → Application type **Desktop app** → Create → **Download JSON**.
5. Save that file as **`secrets/client_secret.json`** in this project (folder is git-ignored).
6. Install deps:
```bash
pip install -r requirements.txt
```
7. First run (any upload command) opens a browser → **sign in and pick "Lulla's Moonlit Garden" (the Brand Account)** in the account chooser, so uploads go to the right channel → grant consent. Token caches to `secrets/token.json`; future runs need no browser.

## Then: one command to publish
```bash
python3 scripts/youtube_upload.py \
  --file renders/song01_full_v2.mp4 \
  --title "Little Light, Goodnight 🌙 Calm Bedtime Songs for Babies | Lulla's Moonlit Garden" \
  --desc-file songs/desc_01.txt \
  --tags "bedtime songs,lullaby,baby sleep music,calm songs for toddlers,nursery rhymes" \
  --thumbnail assets/thumbnail/thumb01_final_A.jpg \
  --publish-at "2026-08-07T16:00:00+05:30"
```

## Good to know
- **Quota (2026):** ~**100 uploads/day** (own bucket) + 10,000 units/day for other calls. Plenty for the cadence + multi-language.
- **Custom thumbnail** still needs the channel **phone-verified** (one-time). Until then, `--thumbnail` fails gracefully and YouTube uses an auto-thumbnail.
- **Made for Kids:** the script sets `selfDeclaredMadeForKids=True` on every upload (compliant by default).
- **New-channel caution:** ramp uploads gradually; don't dump dozens at once from a brand-new channel.
- **Category:** `--category 10` = Music (default), `27` = Education.

## Full auto flow (once set up)
`assemble_video.py` (render) → `youtube_upload.py` (upload + schedule + thumbnail + playlist). The only manual bit left is generating the Suno track (or automate that later via a music API).
