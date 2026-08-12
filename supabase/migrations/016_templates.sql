-- Phase C: template registry — the data-driven replacement for every
-- hardcoded per-channel/per-style branch across edge fn, worker and webapp.
--
-- A template names a production pipeline:
--   produce_style   -> which produce_preview branch the worker runs
--                      ('claude-tricks-v16' | 'cinematic-animatic' |
--                       'sensual-motion' | 'blueprint')
--   plan_style      -> which plan_content prompt the worker uses
--                      ('ai-unpacked' | 'cinematic' | 'blueprint')
--   finalize_script -> deterministic finalize entry (NULL = no finalize
--                      pipeline yet; finalize_episode 409s honestly instead of
--                      running a wrong channel's script)
--   blueprint_source-> repo file cloned as the blueprint skeleton at channel
--                      bring-up (new_channel_scaffold phase='bringup')
--   produce_ui      -> ChannelDetail produce-panel copy
--                      {tag, tag_title, title_ph, brief_ph, flow}
--
-- Channels opt in via factory_channels.template. No template = legacy
-- behavior everywhere (language-abc / pip-moonlit-garden / vehicles keep the
-- staged pipeline untouched).

create table if not exists public.factory_templates (
  key text primary key,
  name text not null,
  description text default '',
  produce_style text not null default 'blueprint',
  plan_style text not null default 'blueprint',
  finalize_script text,
  finalize_tag text default 'v2',
  blueprint_source text,
  aspect text default '9:16',
  runtime_s int default 30,
  model text default 'opus',
  effort text default 'medium',
  produce_ui jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- RLS like the other factory_ tables: enabled, NO policies (service role only)
alter table public.factory_templates enable row level security;

alter table public.factory_channels add column if not exists template text;

-- ── Bespoke templates: the 3 live production pipelines, frozen as rows ──
insert into public.factory_templates
  (key, name, description, produce_style, plan_style, finalize_script, finalize_tag, blueprint_source, aspect, runtime_s, produce_ui)
values
  (
    'ai-unpacked-v16', 'AI Unpacked v16 (avatar host)',
    'Monolithic Ep11/Ep12 Short: Sol avatar host, real on-screen demo, Vaibhav-DNA hooks.',
    'claude-tricks-v16', 'ai-unpacked',
    'scripts/finalize_episode.py', 'v2',
    'channels/claude-tricks/BRAND-BIBLE.md', '9:16', 28,
    '{"tag": "🔒 Ep11/Ep12 template", "tag_title": "Locked craft template — every produce follows Ep11/Ep12", "title_ph": "e.g. Ask AI For a Table, Not a Wall of Text 📊", "brief_ph": "The tip, the on-screen demo, why it''ll go viral, and any facts to verify first…"}'::jsonb
  ),
  (
    'cinematic-animatic-v17', 'Cinematic animatic v17 (host-less)',
    'Host-less cinematic Short: script + VO + animatic preview + 6 motion prompts; human renders motion in Chrome.',
    'cinematic-animatic', 'cinematic',
    'scripts/finalize_already_happening.py', 'v3',
    'channels/already-happening/PRODUCTION-BLUEPRINT.md', '9:16', 38,
    '{"tag": "🔒 Cinematic blueprint", "tag_title": "Locked cinematic blueprint — every produce follows Ep01", "title_ph": "e.g. You''re the last generation that will ever drive a car", "brief_ph": "The topic, the verified TODAY anchor (dated primary source), the +5yr leap, and 6 shot ideas…", "flow": "<strong>Plan content</strong> for grounded-speculation ideas from analytics · breaking AI news · a new life domain · upcoming events — or write your own below. Produces the script + VO + an <strong>animatic preview</strong> and the 6 Wan&nbsp;2.6 motion prompts → review in Studio → generate the 6 clips in Chrome (they replace the placeholders) → <strong>Finalize &amp; Arm</strong>. The <strong>episode number is auto-assigned</strong> when you arm. No calendar needed."}'::jsonb
  ),
  (
    'sensual-motion-v18', 'Sensual-motion Shorts v18 (image→video)',
    'Aashiqana locked recipe: fresh couple anchor → NB2 keyframes → Hailuo motion → stitch → premium brand.',
    'sensual-motion', 'blueprint',
    'scripts/finalize_aashiqana.py', 'v3',
    'channels/aashiqana/SHORTS-TEMPLATE-LOCKED.md', '9:16', 35,
    '{"tag": "🔒 Sensual-motion Shorts template", "tag_title": "Locked recipe — fresh couple → keyframes → Hailuo motion → premium brand", "title_ph": "e.g. Aadhi Raat — 2am situationship, neon rooftop", "brief_ph": "Song concept + mood, couple vibe, the SETTING to rotate to (not the last short), Suno style tags, the hook line…"}'::jsonb
  )
on conflict (key) do nothing;

-- ── Starter templates: what the wizard assigns to NEW channels ──
-- produce_style 'blueprint' = the generic blueprint-driven produce (same path
-- as the incubation Ep01). finalize_script NULL until a deterministic finalize
-- lands for the channel — finalize_episode returns a clear 409 meanwhile.
insert into public.factory_templates
  (key, name, description, produce_style, plan_style, finalize_script, blueprint_source, produce_ui)
values
  (
    'avatar-host', 'Avatar host',
    'Synthetic on-screen host presents tips/news with demos. Cloned from the AI Unpacked build.',
    'blueprint', 'blueprint', null,
    'channels/claude-tricks/BRAND-BIBLE.md',
    '{"tag": "🔒 Channel blueprint", "tag_title": "Locked blueprint — every produce follows your Episode 1 baseline", "title_ph": "Episode title…", "brief_ph": "The idea, the beats, and any facts to verify first…"}'::jsonb
  ),
  (
    'cinematic', 'Host-less cinematic',
    'Cinematic host-less storytelling. Cloned from the Already Happening blueprint.',
    'blueprint', 'blueprint', null,
    'channels/already-happening/PRODUCTION-BLUEPRINT.md',
    '{"tag": "🔒 Channel blueprint", "tag_title": "Locked blueprint — every produce follows your Episode 1 baseline", "title_ph": "Episode title…", "brief_ph": "The idea, the beats, and any facts to verify first…"}'::jsonb
  ),
  (
    'image-story', 'Image → video story',
    'Stills animated into connected motion storytelling. Cloned from the Aashiqana locked template.',
    'blueprint', 'blueprint', null,
    'channels/aashiqana/SHORTS-TEMPLATE-LOCKED.md',
    '{"tag": "🔒 Channel blueprint", "tag_title": "Locked blueprint — every produce follows your Episode 1 baseline", "title_ph": "Episode title…", "brief_ph": "The idea, the beats, and any facts to verify first…"}'::jsonb
  ),
  (
    'baked-text', 'Illustrated / baked-text',
    'Illustrated stills with text baked into the frames. Cloned from the Pip build.',
    'blueprint', 'blueprint', null,
    'channels/pip-moonlit-garden/BRAND-BIBLE.md',
    '{"tag": "🔒 Channel blueprint", "tag_title": "Locked blueprint — every produce follows your Episode 1 baseline", "title_ph": "Episode title…", "brief_ph": "The idea, the beats, and any facts to verify first…"}'::jsonb
  )
on conflict (key) do nothing;

-- ── Backfill the live channels onto their bespoke templates ──
update public.factory_channels set template = 'ai-unpacked-v16'
  where key = 'claude-tricks' and template is null;
update public.factory_channels set template = 'cinematic-animatic-v17'
  where key = 'already-happening' and template is null;
update public.factory_channels set template = 'sensual-motion-v18'
  where key = 'aashiqana' and template is null;
