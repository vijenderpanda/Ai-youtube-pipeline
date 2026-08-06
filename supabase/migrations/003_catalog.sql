-- Factory v3: generator catalog + historical renders
-- (all objects prefixed factory_; shared DB — touch nothing else)

-- Generator catalog fields
alter table public.factory_generators
  add column if not exists category text default 'uncategorized',
  -- category: recording | framing-styles | assembly | audio-voice | captions-lyrics
  --         | art-thumbnails | publishing | automation-infra | channel-tools
  add column if not exists what_it_does text default '',
  add column if not exists inputs jsonb default '[]',
  add column if not exists outputs jsonb default '[]',
  add column if not exists channels jsonb default '[]',
  add column if not exists samples jsonb default '[]';
  -- samples: [{storage_path, title, kind}] pointing at uploaded renders in factory-renders bucket

-- Historical renders
alter table public.factory_renders
  add column if not exists title text,
  add column if not exists generator text,
  add column if not exists origin text default 'job';  -- job | historical

create index if not exists factory_renders_origin_idx
  on public.factory_renders (origin);

create index if not exists factory_renders_generator_idx
  on public.factory_renders (generator);
