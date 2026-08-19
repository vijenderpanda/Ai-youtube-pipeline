// factory-api — single edge function backing the YouTube content-factory dashboard.
// Auth: sha256(x-factory-token) must match factory_settings.token_sha256.
// Uses service role key (auto-injected) — RLS on factory_* tables has no policies.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import * as postgres from "https://deno.land/x/postgres@v0.17.0/mod.ts";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-factory-token, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

const JOB_TYPES = [
  // produce_short removed 2026-08-07 — production is staged-only ("produce in stages").
  // The only produce path is plan_assets, via the queue/stage/supersede calendar actions.
  "record_demo",
  "custom",
  "new_channel_scaffold",
  "analytics_sync",
  "analyze_and_suggest",
  // v8: staged production ("Studio") — see docs/STAGED-PIPELINE.md
  "plan_assets",
  "generate_asset",
  "assemble_episode",
  "preview_episode",
  // v16: monolithic one-Claude-call production that stops at a low-res preview
  // (raw MP4, no mastering). Human reviews in Studio, then finalize_episode.py
  // (via shell_script) runs mastering + endcard + outro + arm YT. Cost saving
  // vs full produce_short: ~$1-2/short. See build_ep_v2.py --preview flag.
  "produce_preview",
  // v17: channel-page idea engine — ranked ideas across analytics / Vaibhav-DNA /
  // news / upcoming events. Structured result (job.result.ideas), no renders.
  "plan_content",
  // v18: channel-creation wizard — per-step conversational suggestion engine.
  // Structured result (job.result: {options,question,ready_to_advance}), no renders.
  "channel_intake",
];
// v8: staged job types carry meta.calendar_id for their episode
const STAGED_JOB_TYPES = ["plan_assets", "generate_asset", "assemble_episode", "preview_episode"];
// Calendar items keep 'produce_short' as a legacy content-type LABEL (staging ignores it —
// content is always produced via plan_assets). So calendar validation still allows it, even
// though create_job (2026-08-07) no longer does.
const CALENDAR_TYPES = ["produce_short", ...JOB_TYPES];
const EFFORTS = ["low", "medium", "high", "xhigh", "max"];
// Statuses settable via update_calendar_item (queued/produced are set by queue route / worker)
const CALENDAR_PATCH_STATUSES = ["planned", "suggested", "skipped"];
// v3: render provenance filter values (?r=renders&origin=)
const RENDER_ORIGINS = ["job", "historical"];
// v4: calendar kind filter values (?r=calendar&kind=)
const CALENDAR_KINDS = ["content", "factory"];
// v6: cheap uuid shape check so bad ids get a 400 instead of a pg error
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
// v19: ?r=suggestions reads this many candidate rows before the evidence guard
// runs, so `limit` counts suggestions that actually SHIP, not rows dropped for
// having no citations. Comfortably above the live standalone-suggestion count.
const SUGGESTION_POOL = 200;
// v4: post fields patchable via update_post
const POST_PATCH_FIELDS = [
  "yt_title",
  "yt_description",
  "tags",
  "publish_at",
  "audience",
  "synthetic",
];
// Phase 3: hard ceiling on the provenance scan behind ?r=asset_backlinks. One
// build writes ~18 rows, so this covers hundreds of episodes; the endpoint is a
// usage HINT, and `recorded_since` is asked for separately so truncating the
// scan can never move the "attribution starts here" date.
const PROVENANCE_SCAN_MAX = 5000;
// v7: + control, heartbeat_at (job-control: stop requests + worker liveness)
const JOB_LIST_COLS =
  "id, channel_key, type, title, prompt, model, effort, status, result, meta, error, created_at, started_at, finished_at, control, heartbeat_at, assigned_worker, target_worker";

// Sprint 2 — the LOCKED composition template vocabulary. A template version's
// draft carries an editable block SEQUENCE (factory_template_blocks); lock
// freezes it into composition._sequence, and build_ep_v2 turns that into
// spec.segments. The designer UI, this edge validator and the Remotion Short all
// share these three vocabularies (kept in sync with the SHARED CONTRACT).
//
// The 13 graphical b-roll components — mirror of
// remotion-studio/src/cookbook/registry.ts. Exposed via GET ?r=cookbook so the
// designer palette and set_template_version_block's validator read ONE source.
const COOKBOOK_CATALOG: { id: string; label: string; role: string; needs: string }[] = [
  { id: "ChatApp", label: "AI chat app", role: "app-ui", needs: "dialogue" },
  { id: "LineReveal", label: "Line/area trend reveal", role: "dataviz", needs: "series" },
  { id: "CommandPalette", label: "Command palette (⌘K)", role: "interaction", needs: "query-results" },
  { id: "BentoGrid", label: "Bento fact grid", role: "layout", needs: "facts" },
  { id: "DiffReveal", label: "Before → after rewrite", role: "transformation", needs: "before-after" },
  { id: "RingGauge", label: "Concentric ring gauge", role: "dataviz", needs: "metrics" },
  { id: "Odometer", label: "Rolling number", role: "interaction", needs: "single-number" },
  { id: "OrbitNodes", label: "Hub + orbit constellation", role: "interaction", needs: "hub-spokes" },
  { id: "KineticQuote", label: "Kinetic punchline", role: "typography", needs: "phrase" },
  { id: "NotificationStack", label: "Phone alert pile", role: "device-ui", needs: "alerts" },
  { id: "DynamicIsland", label: "Live-activity island", role: "device-ui", needs: "steps" },
  { id: "VoiceOrb", label: "Voice assistant orb", role: "device-ui", needs: "utterance" },
  { id: "SwipeDeck", label: "Decision swipe deck", role: "interaction", needs: "options" },
  // wow-mechanics (registry.ts adds these; the render map COOKBOOK_COMPONENTS and
  // this validator must carry them too or set_template_version_block 400s a valid id
  // OR a loud placeholder renders — keep all three in sync, this list never leads).
  { id: "Fogline", label: "Agent plan / lit road", role: "app-ui", needs: "steps" },
  { id: "HoloCard", label: "Holographic hero card", role: "layout", needs: "facts" },
  { id: "GlassPanel", label: "Liquid-glass stat panel", role: "device-ui", needs: "single-number" },
  { id: "MorphField", label: "Button → field → confirm", role: "interaction", needs: "steps" },
];
const COOKBOOK_IDS = new Set(COOKBOOK_CATALOG.map((c) => c.id));
// The 6 spatial layout ids (remotion-studio/src/layouts.ts) a slot/spatial block
// may name, and the 7 block types a composition sequence is built from.
const LAYOUT_IDS = new Set(["full-broll", "host-top", "host-bottom", "split", "host-pip", "framed"]);
const BLOCK_TYPES = new Set(["hook", "host", "broll", "statbars", "outro", "slot", "cards"]);

const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  { auth: { persistSession: false } },
);

// v5: direct Postgres pool (SUPABASE_DB_URL is auto-injected) for SQL-side
// aggregation (?r=video_summary). Lazy — no connection until first use.
const pgPool = new postgres.Pool(Deno.env.get("SUPABASE_DB_URL")!, 2, true);

// v5: per-video aggregates over a date window, weighted avg_view_pct by views,
// trend = daily views ordered by date. Single query; returns jsonb so numeric
// values serialize as JSON numbers.
const VIDEO_SUMMARY_SQL = `
with s as (
  select
    video_id,
    (array_agg(channel_key order by date desc))[1] as channel_key,
    (array_agg(title order by date desc) filter (where title is not null))[1] as title,
    coalesce(sum(views), 0)::bigint as total_views,
    sum(watch_minutes) as watch_minutes,
    case
      when coalesce(sum(views) filter (where avg_view_pct is not null), 0) > 0
        then sum(avg_view_pct * views) filter (where avg_view_pct is not null)
             / sum(views) filter (where avg_view_pct is not null)
      else null
    end as avg_view_pct,
    sum(subs_gained)::bigint as subs_gained,
    sum(likes)::bigint as likes,
    sum(comments)::bigint as comments,
    sum(shares)::bigint as shares,
    -- window signals (traffic mix + retention holds): stamped on the latest daily
    -- row per video, so take the most-recent non-null.
    (array_agg(shorts_pct  order by date desc) filter (where shorts_pct  is not null))[1] as shorts_pct,
    (array_agg(hold_3s     order by date desc) filter (where hold_3s     is not null))[1] as hold_3s,
    (array_agg(hold_15s    order by date desc) filter (where hold_15s    is not null))[1] as hold_15s,
    (array_agg(traffic_mix order by date desc) filter (where traffic_mix is not null))[1] as traffic_mix,
    min(date) as first_date,
    max(date) as last_date,
    array_agg(coalesce(views, 0) order by date asc) as trend
  from public.factory_video_stats
  where ($1::text is null or channel_key = $1)
    and date >= $2::date
  group by video_id
)
select coalesce(jsonb_agg(to_jsonb(s) order by s.total_views desc), '[]'::jsonb) as videos
from s
`;

// v12: sync-to-sync deltas. Per video, diff its two most recent snapshots. `prev`
// is computed PER VIDEO (not a single global "second-newest sync_at") so a channel
// that errored in one run doesn't make all its videos falsely read as new. is_new
// rows get null deltas (a first-seen video must not dump its whole lifetime into
// the network sum). rank_change > 0 means the video climbed. Read-only.
const VIDEO_DELTAS_SQL = `
with cur as (
  select distinct on (video_id) *
  from public.factory_video_snapshots
  where ($1::text is null or channel_key = $1)
  order by video_id, sync_at desc
),
prev as (
  select distinct on (s.video_id) s.*
  from public.factory_video_snapshots s
  join cur c on c.video_id = s.video_id and s.sync_at < c.sync_at
  order by s.video_id, s.sync_at desc
),
d as (
  select
    cur.video_id,
    cur.channel_key,
    cur.title,
    cur.source,
    cur.window_views,
    cur.window_days,
    cur.avg_view_pct,
    cur.shares,
    cur.views       as views_now,
    cur.rank        as rank_now,
    prev.rank       as rank_prev,
    cur.sync_at     as cur_sync_at,
    prev.sync_at    as prev_sync_at,
    (prev.video_id is null) as is_new,
    case when prev.video_id is null then null else cur.views - prev.views end as d_views,
    case when prev.video_id is null then null else cur.likes - prev.likes end as d_likes,
    case when prev.video_id is null then null else cur.comments - prev.comments end as d_comments,
    case when prev.video_id is null or prev.rank is null or cur.rank is null
         then null else prev.rank - cur.rank end as rank_change
  from cur left join prev on prev.video_id = cur.video_id
)
select jsonb_build_object(
  'cur_sync_at',  (select max(cur_sync_at) from d),
  'prev_sync_at', (select max(prev_sync_at) from d),
  'is_first',     coalesce((select bool_and(is_new) from d), true),
  'videos',       coalesce(jsonb_agg(to_jsonb(d) order by d.window_views desc nulls last), '[]'::jsonb)
) as result
from d
`;

// v12: recent syncs with per-sync network totals (small "growth per sync" trend).
const SYNC_LOG_SQL = `
select coalesce(jsonb_agg(to_jsonb(t) order by t.sync_at desc), '[]'::jsonb) as syncs
from (
  select sync_at,
         count(*)::int      as videos,
         sum(views)::bigint as total_views,
         sum(window_views)::bigint as window_views
  from public.factory_video_snapshots
  where ($1::text is null or channel_key = $1)
  group by sync_at
  order by sync_at desc
  limit $2::int
) t
`;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

async function sha256Hex(s: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function logEvent(kind: string, message: string, meta: Record<string, unknown> = {}) {
  await db.from("factory_events").insert({ kind, message, meta });
}

function clampLimit(raw: string | null, def: number, max: number): number {
  const n = raw === null ? def : parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1) return def;
  return Math.min(n, max);
}

// v8: THE staged-production entry point — lifted verbatim out of
// `case "stage_calendar_item"` so `case "accept_suggestion"` (v19) can reuse it
// instead of forking it. Guards, job shape, status transition and the
// { item, job } response body are unchanged; the caller validates `id` first.
async function stageCalendarItem(id: string): Promise<Response> {
  const { data: item, error: itemErr } = await db.from("factory_calendar")
    .select("*").eq("id", id).maybeSingle();
  if (itemErr) return json({ error: itemErr.message }, 500);
  if (!item) return json({ error: "calendar item not found" }, 404);
  if (item.status !== "planned" && item.status !== "suggested") {
    return json({
      error: "calendar item must be planned or suggested to stage (status: " + item.status + ")",
    }, 409);
  }
  const { count: assetCount, error: countErr } = await db.from("factory_assets")
    .select("id", { count: "exact", head: true }).eq("calendar_id", id);
  if (countErr) return json({ error: countErr.message }, 500);
  if ((assetCount ?? 0) > 0) {
    return json({ error: "calendar item already has staged assets — open its Studio board instead" }, 409);
  }
  const { data: job, error: jobErr } = await db.from("factory_jobs")
    .insert({
      channel_key: item.channel_key,
      type: "plan_assets",
      title: "Plan assets — " + item.title,
      prompt: item.brief,
      model: item.model,
      effort: item.effort,
      ultracode: item.ultracode,
      status: "queued",
      meta: { calendar_id: item.id },
    })
    .select().single();
  if (jobErr) return json({ error: jobErr.message }, 500);
  const { data: updated, error: updErr } = await db.from("factory_calendar")
    .update({ status: "queued", production_mode: "staged", job_id: job.id })
    .eq("id", id).select().single();
  if (updErr) return json({ error: updErr.message }, 500);
  await logEvent(
    "assets_staged",
    `Staged production queued for '${item.title}' (${item.channel_key})`,
    { item_id: id, job_id: job.id, channel_key: item.channel_key },
  );
  return json({ item: updated, job });
}

// v8: asset actions only apply to the LATEST version of an asset_key
// deno-lint-ignore no-explicit-any
async function isLatestAssetVersion(asset: any): Promise<{ latest: boolean; error: string | null }> {
  const { data, error } = await db.from("factory_assets")
    .select("version")
    .eq("calendar_id", asset.calendar_id)
    .eq("asset_key", asset.asset_key)
    .order("version", { ascending: false })
    .limit(1);
  if (error) return { latest: false, error: error.message };
  return { latest: (data?.[0]?.version ?? asset.version) === asset.version, error: null };
}

async function handleGet(url: URL): Promise<Response> {
  const r = url.searchParams.get("r");

  switch (r) {
    case "overview": {
      const [channels, jobs, events, jobsDone, jobsFailed, renders, channelCount, lastSync] =
        await Promise.all([
          db.from("factory_channels").select("*").order("created_at", { ascending: true }),
          db.from("factory_jobs").select(JOB_LIST_COLS)
            .order("created_at", { ascending: false }).limit(10),
          db.from("factory_events").select("*").order("ts", { ascending: false }).limit(15),
          db.from("factory_jobs").select("id", { count: "exact", head: true }).eq("status", "done"),
          db.from("factory_jobs").select("id", { count: "exact", head: true }).eq("status", "failed"),
          db.from("factory_renders").select("id", { count: "exact", head: true }),
          db.from("factory_channels").select("key", { count: "exact", head: true }),
          // v6: worker-maintained last analytics sync timestamp (null ok)
          db.from("factory_settings").select("value").eq("key", "last_sync_at").maybeSingle(),
        ]);
      const err = channels.error || jobs.error || events.error || jobsDone.error ||
        jobsFailed.error || renders.error || channelCount.error || lastSync.error;
      if (err) return json({ error: err.message }, 500);
      return json({
        channels: channels.data,
        recent_jobs: jobs.data,
        recent_events: events.data,
        last_sync_at: lastSync.data?.value ?? null,
        totals: {
          jobs_done: jobsDone.count ?? 0,
          jobs_failed: jobsFailed.count ?? 0,
          renders: renders.count ?? 0,
          channels: channelCount.count ?? 0,
        },
      });
    }

    case "channels": {
      const { data, error } = await db.from("factory_channels").select("*")
        .order("created_at", { ascending: true });
      if (error) return json({ error: error.message }, 500);
      return json({ channels: data });
    }

    // v19: the template registry — every production pipeline as data
    // (produce_style / plan_style / finalize routing / produce-panel copy).
    case "templates": {
      const { data, error } = await db.from("factory_templates").select("*")
        .order("created_at", { ascending: true });
      if (error) return json({ error: error.message }, 500);
      return json({ templates: data });
    }

    // Phase 1 — Studio "Assets" board: brand-asset versions + their locks.
    // versions ordered asset_type asc, version desc; optional ?channel= filter.
    // Mirrors the "templates" single-table read + the "jobs" channel filter.
    case "assets": {
      let vq = db.from("factory_asset_versions").select("*")
        .order("asset_type", { ascending: true })
        .order("version", { ascending: false });
      const channel = url.searchParams.get("channel");
      if (channel) vq = vq.eq("channel_key", channel);
      // Phase 4: retired revisions ship by DEFAULT (the Assets board renders them
      // struck-through, and the composer needs them to explain a disabled pick).
      // `?include_retired=0` is the opt-OUT for callers that want a clean list.
      if (url.searchParams.get("include_retired") === "0") vq = vq.neq("status", "retired");
      const [versions, locks] = await Promise.all([
        vq,
        db.from("factory_asset_locks").select("*"),
      ]);
      if (versions.error) return json({ error: versions.error.message }, 500);
      if (locks.error) return json({ error: locks.error.message }, 500);
      return json({ versions: versions.data, locks: locks.data });
    }

    // Phase 4 — the Template Composer. factory_templates names the PIPELINE;
    // a template VERSION names the CAST it runs with. Returns three flat arrays
    // the client joins (same shape as the ?r=assets versions+locks pair):
    //   versions       — factory_template_versions, template_key asc / version desc
    //   assets         — factory_template_assets rows of those versions (the
    //                    EDITABLE composition of a draft)
    //   asset_versions — the factory_asset_versions rows those slots point at,
    //                    so the composer can draw a thumb + label + v# without a
    //                    second round trip.
    // Filters: ?template_key= · ?channel= · ?include_retired=1 (retired versions
    // are hidden by default so the composer's version rail stays readable).
    case "template_versions": {
      let tvq = db.from("factory_template_versions").select("*")
        .order("template_key", { ascending: true })
        .order("version", { ascending: false });
      const tKey = url.searchParams.get("template_key");
      if (tKey) tvq = tvq.eq("template_key", tKey);
      const tChan = url.searchParams.get("channel");
      if (tChan) tvq = tvq.eq("channel_key", tChan);
      if (url.searchParams.get("include_retired") !== "1") tvq = tvq.neq("status", "retired");
      const { data: tVersions, error: tvErr } = await tvq;
      if (tvErr) return json({ error: tvErr.message }, 500);
      const tvIds = (tVersions ?? []).map((v) => v.id);
      if (tvIds.length === 0) {
        return json({ versions: tVersions ?? [], assets: [], asset_versions: [], blocks: [] });
      }
      const { data: tAssets, error: taErr } = await db.from("factory_template_assets")
        .select("*").in("template_version_id", tvIds)
        .order("asset_type", { ascending: true })
        .order("position", { ascending: true });
      if (taErr) return json({ error: taErr.message }, 500);
      const avIds = [
        ...new Set((tAssets ?? []).map((a) => a.asset_version_id)),
      ];
      let avRows: unknown[] = [];
      if (avIds.length > 0) {
        const { data: avData, error: avErr } = await db.from("factory_asset_versions")
          .select("id, channel_key, asset_type, version, label, status, storage_path, thumb_path, meta")
          .in("id", avIds);
        if (avErr) return json({ error: avErr.message }, 500);
        avRows = avData ?? [];
      }
      // Sprint 2: the draft-editable composition SEQUENCE for these versions,
      // returned as a 4th flat array the designer joins by template_version_id.
      const { data: tBlocks, error: tbErr } = await db.from("factory_template_blocks")
        .select("*").in("template_version_id", tvIds)
        .order("position", { ascending: true });
      if (tbErr) return json({ error: tbErr.message }, 500);
      return json({
        versions: tVersions, assets: tAssets ?? [],
        asset_versions: avRows, blocks: tBlocks ?? [],
      });
    }

    // Sprint 2 — the cookbook CATALOG: the 13 graphical b-roll components the
    // composition designer can drop into a broll/slot block, plus the layout ids
    // and block types the sequence is built from. ONE source shared by the
    // designer palette and set_template_version_block's validator, so an unknown
    // id can never slip into a locked _sequence. Mirrors
    // remotion-studio/src/cookbook/registry.ts.
    case "cookbook": {
      return json({
        cookbook: COOKBOOK_CATALOG,
        layouts: [...LAYOUT_IDS],
        block_types: [...BLOCK_TYPES],
      });
    }

    // Phase 3 — asset BACKLINKS: "where has this revision actually been used?"
    //
    // factory_episode_assets_used is written by build_ep_v2._flush_provenance()
    // on every build, so this is OBSERVED history — never inferred from today's
    // locks (moving a lock must not rewrite the past).
    //
    // HONESTY CONTRACT: provenance recording only began when migration 021
    // shipped. A missing entry means NOT RECORDED, not "never used" — a revision
    // that shipped twenty times before that day has no rows here. Clients MUST
    // render absence as blank/—, never as 0. `recorded_since` is the oldest row
    // we hold, so the UI can state exactly how far back attribution goes.
    //
    // Response (the client indexes usage[version_id] directly):
    //   { usage: { "<asset_version_id>": {
    //       episodes: 3,          // DISTINCT calendar_ids that built with it
    //       shipped: 2,           // …of those, ones whose post has a video_id
    //       casts: 1,             // template versions currently composing it
    //       last_used_at: "2026-08-18T…" | null,
    //       videos: [{ calendar_id, video_id, yt_title, publish_at }],  // ≤5, newest first
    //       template_versions: [{ id, template_key, label, version, status }]
    //     }, … },
    //     recorded_since: "2026-08-18T…" | null,
    //     totals: { rows, versions, episodes, unattributed } }
    // A version_id absent from `usage` has NO recorded use — that is all it means.
    // Filters: ?channel= · ?include_retired=1 (retired casts are excluded by
    // default, mirroring ?r=template_versions).
    case "asset_backlinks": {
      const channel = url.searchParams.get("channel");

      let uq = db.from("factory_episode_assets_used")
        .select("version_id, calendar_id, created_at")
        .not("version_id", "is", null)
        .order("created_at", { ascending: false })
        .limit(PROVENANCE_SCAN_MAX);
      if (channel) uq = uq.eq("channel_key", channel);

      // oldest row = the honest "attribution starts here" date, asked for
      // separately so the answer stays right even if the scan above truncates.
      let sq = db.from("factory_episode_assets_used")
        .select("created_at").order("created_at", { ascending: true }).limit(1);
      if (channel) sq = sq.eq("channel_key", channel);

      let tvq = db.from("factory_template_versions")
        .select("id, template_key, label, version, status");
      if (channel) tvq = tvq.eq("channel_key", channel);
      if (url.searchParams.get("include_retired") !== "1") tvq = tvq.neq("status", "retired");

      const [used, since, tVersions] = await Promise.all([uq, sq, tvq]);
      if (used.error) return json({ error: used.error.message }, 500);
      if (since.error) return json({ error: since.error.message }, 500);
      if (tVersions.error) return json({ error: tVersions.error.message }, 500);

      type Shipped = {
        calendar_id: string;
        video_id: string;
        yt_title: string | null;
        publish_at: string | null;
      };
      type CastRef = {
        id: string;
        template_key: string;
        label: string | null;
        version: number;
        status: string;
      };
      type Entry = {
        episodes: number;
        shipped: number;
        casts: number;
        last_used_at: string | null;
        videos: Shipped[];
        template_versions: CastRef[];
      };
      const usage: Record<string, Entry> = {};
      const entryFor = (id: string): Entry =>
        usage[id] ?? (usage[id] = {
          episodes: 0,
          shipped: 0,
          casts: 0,
          last_used_at: null,
          videos: [],
          template_versions: [],
        });

      // One build writes one row per resolved slot, and a re-cut writes them
      // again — DISTINCT calendar_id is what makes "3 eps" true rather than
      // "3 rows". Rows with no calendar_id can't be attributed to an episode,
      // so they are counted in totals only.
      const calsByVersion: Record<string, Set<string>> = {};
      const allCals = new Set<string>();
      let unattributed = 0;
      for (const row of used.data ?? []) {
        const vid = row.version_id as string;
        if (!row.calendar_id) {
          unattributed += 1;
          continue;
        }
        const e = entryFor(vid);
        // rows arrive created_at desc, so the first one we see is the newest
        if (!e.last_used_at) e.last_used_at = row.created_at;
        (calsByVersion[vid] ?? (calsByVersion[vid] = new Set())).add(row.calendar_id);
        allCals.add(row.calendar_id);
      }

      // shipped = that calendar item has a post carrying a real video_id.
      // A re-arm can leave a superseded post behind, so newest publish_at wins.
      const postByCal: Record<string, Shipped> = {};
      const calIds = [...allCals];
      if (calIds.length > 0) {
        const { data: posts, error: pErr } = await db.from("factory_posts")
          .select("calendar_id, video_id, yt_title, publish_at")
          .in("calendar_id", calIds)
          .not("video_id", "is", null)
          .order("publish_at", { ascending: false, nullsFirst: false });
        if (pErr) return json({ error: pErr.message }, 500);
        for (const p of posts ?? []) {
          if (postByCal[p.calendar_id]) continue;
          postByCal[p.calendar_id] = {
            calendar_id: p.calendar_id,
            video_id: p.video_id,
            yt_title: p.yt_title ?? null,
            publish_at: p.publish_at ?? null,
          };
        }
      }

      for (const [vid, cals] of Object.entries(calsByVersion)) {
        const e = entryFor(vid);
        e.episodes = cals.size;
        const vids: Shipped[] = [];
        for (const c of cals) if (postByCal[c]) vids.push(postByCal[c]);
        vids.sort((a, b) =>
          String(b.publish_at ?? "").localeCompare(String(a.publish_at ?? ""))
        );
        e.shipped = vids.length;
        e.videos = vids.slice(0, 5);
      }

      // …and which composed casts point at it today (factory_template_assets).
      const tvById: Record<string, CastRef> = {};
      for (const v of tVersions.data ?? []) tvById[v.id] = v;
      const tvIds = Object.keys(tvById);
      if (tvIds.length > 0) {
        const { data: tAssets, error: taErr } = await db.from("factory_template_assets")
          .select("asset_version_id, template_version_id")
          .in("template_version_id", tvIds);
        if (taErr) return json({ error: taErr.message }, 500);
        // a cast can hold the same revision at position 0 AND as an alt — count
        // the CAST once, not the slot rows.
        const seen = new Set<string>();
        for (const a of tAssets ?? []) {
          const k = a.asset_version_id + ":" + a.template_version_id;
          if (seen.has(k)) continue;
          seen.add(k);
          const tv = tvById[a.template_version_id];
          if (!tv) continue;
          const e = entryFor(a.asset_version_id);
          e.casts += 1;
          e.template_versions.push(tv);
        }
      }

      return json({
        usage,
        recorded_since: since.data?.[0]?.created_at ?? null,
        totals: {
          rows: (used.data ?? []).length,
          versions: Object.keys(usage).length,
          episodes: allCals.size,
          unattributed,
        },
      });
    }

    case "jobs": {
      const limit = clampLimit(url.searchParams.get("limit"), 50, 200);
      let q = db.from("factory_jobs").select(JOB_LIST_COLS)
        .order("created_at", { ascending: false }).limit(limit);
      const channel = url.searchParams.get("channel");
      if (channel) q = q.eq("channel_key", channel);
      const { data, error } = await q;
      if (error) return json({ error: error.message }, 500);
      return json({ jobs: data });
    }

    case "job": {
      const id = url.searchParams.get("id");
      if (!id) return json({ error: "id required" }, 400);
      const { data, error } = await db.from("factory_jobs").select("*").eq("id", id).maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "job not found" }, 404);
      return json({ job: data });
    }

    // v18: reload an in-progress channel-wizard draft (resume/refresh)
    case "channel_draft": {
      const id = url.searchParams.get("id");
      if (!id || !UUID_RE.test(id)) return json({ error: "id (uuid) required" }, 400);
      const { data, error } = await db.from("factory_channel_drafts")
        .select("*").eq("id", id).maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "draft not found" }, 404);
      return json({ draft: data });
    }

    case "renders": {
      let q = db.from("factory_renders").select("*")
        .order("created_at", { ascending: false }).limit(100);
      const channel = url.searchParams.get("channel");
      if (channel) q = q.eq("channel_key", channel);
      const origin = url.searchParams.get("origin");
      if (origin) {
        if (!RENDER_ORIGINS.includes(origin)) {
          return json({ error: "origin must be one of: " + RENDER_ORIGINS.join(" | ") }, 400);
        }
        q = q.eq("origin", origin);
      }
      const generator = url.searchParams.get("generator");
      if (generator) q = q.eq("generator", generator);
      const { data, error } = await q;
      if (error) return json({ error: error.message }, 500);
      return json({ renders: data });
    }

    case "generators": {
      // v3: select * includes catalog fields (category, what_it_does, inputs,
      // outputs, channels, samples); v4 adds tags + scope
      const { data, error } = await db.from("factory_generators").select("*")
        .order("name", { ascending: true });
      if (error) return json({ error: error.message }, 500);
      return json({ generators: data });
    }

    // v6: rows include replaces_id/why_not (select * picks up the new columns)
    case "calendar": {
      const dayMs = 86400000;
      const fmt = (d: Date) => d.toISOString().slice(0, 10);
      const from = url.searchParams.get("from") ?? fmt(new Date(Date.now() - 7 * dayMs));
      const to = url.searchParams.get("to") ?? fmt(new Date(Date.now() + 30 * dayMs));
      let q = db.from("factory_calendar").select("*")
        .gte("planned_date", from)
        .lte("planned_date", to)
        .order("planned_date", { ascending: true });
      const channel = url.searchParams.get("channel");
      if (channel) q = q.eq("channel_key", channel);
      // v4: kind filter (content | factory)
      const kind = url.searchParams.get("kind");
      if (kind) {
        if (!CALENDAR_KINDS.includes(kind)) {
          return json({ error: "kind must be one of: " + CALENDAR_KINDS.join(" | ") }, 400);
        }
        q = q.eq("kind", kind);
      }
      const { data, error } = await q;
      if (error) return json({ error: error.message }, 500);
      return json({ items: data });
    }

    // v19: the Studio suggestion shelf — research-backed "what to make next".
    //
    // Deliberately does NOT inherit ?r=calendar's now-7d … now+30d window: a
    // suggestion parked a cadence out (chore/blocker cards) would be silently
    // dropped by it, and "silently dropped" is the one thing this shelf may
    // never do. Ordering is planned_date asc so the nearest slot leads.
    //
    // `replaces_id is null` is the server-side twin of Calendar.jsx's
    // challengerByTarget/hiddenChallengerIds logic: a challenger row attaches
    // to an original and must NEVER render standalone in the launcher.
    case "suggestions": {
      const limit = clampLimit(url.searchParams.get("limit"), 6, 24);
      // Over-fetch, THEN guard, THEN slice. The black-box guard below is not
      // expressible as a PostgREST filter, and there are ~10x more evidence-less
      // pre-022 'suggested' rows than real ones — applying `limit` in SQL would
      // spend the whole budget on rows the guard then drops and hand back an
      // empty shelf. SUGGESTION_POOL is the read cap; `limit` is what ships.
      let q = db.from("factory_calendar").select("*")
        .eq("status", "suggested")
        .eq("kind", "content")
        .is("replaces_id", null)
        .order("planned_date", { ascending: true })
        .limit(SUGGESTION_POOL);
      const channel = url.searchParams.get("channel");
      if (channel) q = q.eq("channel_key", channel);
      const { data, error } = await q;
      if (error) return json({ error: error.message }, 500);
      // Black-box guard, read side. scripts/suggest_next.py asserts non-empty
      // cites[] on the write side; this is the belt to that pair of braces, and
      // it also hides the pre-022 legacy rows that never carried evidence. An
      // ai_suggestion that cannot show its work does not get shown.
      const items = (data ?? []).filter((r) =>
        r.origin !== "ai_suggestion" ||
        (r.evidence && Array.isArray(r.evidence.cites) && r.evidence.cites.length > 0)
      ).slice(0, limit);
      return json({ items });
    }

    // v4: publish pipeline posts
    case "posts": {
      const limit = clampLimit(url.searchParams.get("limit"), 100, 200);
      let q = db.from("factory_posts").select("*")
        .order("created_at", { ascending: false }).limit(limit);
      const status = url.searchParams.get("status");
      if (status) q = q.eq("status", status);
      const channel = url.searchParams.get("channel");
      if (channel) q = q.eq("channel_key", channel);
      const { data, error } = await q;
      if (error) return json({ error: error.message }, 500);
      return json({ posts: data });
    }

    // v4: analytics/AI insights feed
    case "insights": {
      const limit = clampLimit(url.searchParams.get("limit"), 50, 200);
      let q = db.from("factory_insights").select("*")
        .order("ts", { ascending: false }).limit(limit);
      const channel = url.searchParams.get("channel");
      if (channel) q = q.eq("channel_key", channel);
      const { data, error } = await q;
      if (error) return json({ error: error.message }, 500);
      return json({ insights: data });
    }

    // v4: last 3 renders a generator contributed to
    // (via factory_render_contributors; fallback: factory_renders.generator)
    case "generator_samples": {
      const name = url.searchParams.get("name");
      if (!name) return json({ error: "name required" }, 400);
      const { data: contribs, error: cErr } = await db.from("factory_render_contributors")
        .select("render_id, role").eq("generator", name)
        .order("id", { ascending: false }).limit(3);
      if (cErr) return json({ error: cErr.message }, 500);
      if (contribs && contribs.length > 0) {
        const ids = contribs.map((c) => c.render_id);
        const { data: renders, error: rErr } = await db.from("factory_renders")
          .select("*").in("id", ids);
        if (rErr) return json({ error: rErr.message }, 500);
        const byId = new Map((renders ?? []).map((r) => [r.id, r]));
        const samples = contribs
          .filter((c) => byId.has(c.render_id))
          .map((c) => ({ render: byId.get(c.render_id), role: c.role }));
        return json({ samples });
      }
      const { data: renders, error: rErr } = await db.from("factory_renders")
        .select("*").eq("generator", name)
        .order("created_at", { ascending: false }).limit(3);
      if (rErr) return json({ error: rErr.message }, 500);
      const samples = (renders ?? []).map((r) => ({ render: r, role: null }));
      return json({ samples });
    }

    // v4.1: daily stats series from factory_stats (?r=stats&channel=K&days=N)
    // (worker's analytics_sync aggregates history.csv into factory_stats)
    case "stats": {
      const days = clampLimit(url.searchParams.get("days"), 90, 365);
      const from = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
      let q = db.from("factory_stats")
        .select("channel_key, date, views, subs")
        .gte("date", from)
        .order("date", { ascending: true });
      const channel = url.searchParams.get("channel");
      if (channel) q = q.eq("channel_key", channel);
      const { data, error } = await q;
      if (error) return json({ error: error.message }, 500);
      return json({ stats: data });
    }

    // v5: raw per-video daily rows (?r=video_stats&channel=K&days=N)
    case "video_stats": {
      const days = clampLimit(url.searchParams.get("days"), 30, 90);
      const from = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
      let q = db.from("factory_video_stats").select("*")
        .gte("date", from)
        .order("date", { ascending: false })
        .order("views", { ascending: false });
      const channel = url.searchParams.get("channel");
      if (channel) q = q.eq("channel_key", channel);
      const { data, error } = await q;
      if (error) return json({ error: error.message }, 500);
      return json({ rows: data });
    }

    // v5: per-video aggregates over the window (?r=video_summary&channel=K&days=N)
    // computed in a single SQL query (weighted avg_view_pct, trend array)
    case "video_summary": {
      const days = clampLimit(url.searchParams.get("days"), 30, 90);
      const from = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
      const channel = url.searchParams.get("channel");
      const conn = await pgPool.connect();
      try {
        const result = await conn.queryObject<{ videos: unknown }>({
          text: VIDEO_SUMMARY_SQL,
          args: [channel, from],
        });
        return json({ videos: result.rows[0]?.videos ?? [] });
      } finally {
        conn.release();
      }
    }

    // v12: sync-to-sync deltas (?r=video_deltas&channel=K) — per-video diff of the
    // two most recent snapshots + is_first flag for the baseline empty state.
    case "video_deltas": {
      const channel = url.searchParams.get("channel");
      const conn = await pgPool.connect();
      try {
        const result = await conn.queryObject<{ result: unknown }>({
          text: VIDEO_DELTAS_SQL,
          args: [channel],
        });
        return json(result.rows[0]?.result ?? { cur_sync_at: null, is_first: true, videos: [] });
      } finally {
        conn.release();
      }
    }

    // v12: recent syncs with network totals (?r=sync_log&channel=K&limit=N)
    case "sync_log": {
      const limit = clampLimit(url.searchParams.get("limit"), 10, 60);
      const channel = url.searchParams.get("channel");
      const conn = await pgPool.connect();
      try {
        const result = await conn.queryObject<{ syncs: unknown }>({
          text: SYNC_LOG_SQL,
          args: [channel, limit],
        });
        return json({ syncs: result.rows[0]?.syncs ?? [] });
      } finally {
        conn.release();
      }
    }

    // v8: staged episodes in flight + per-item asset counts
    // (counts over the LATEST version of each asset_key only)
    // v16: direct-mode calendar items with ≥1 asset row also surface here —
    // produce_preview jobs run in direct mode and push assets via
    // scripts/push_asset.py so Studio's filmstrip populates during the
    // Claude session. A direct row with 0 assets is a plain calendar
    // item (no in-flight production) and stays out of Studio.
    case "staged": {
      const { data: items, error } = await db.from("factory_calendar").select("*")
        .in("production_mode", ["staged", "direct"])
        .in("status", ["queued", "produced"])
        .order("planned_date", { ascending: true });
      if (error) return json({ error: error.message }, 500);
      const counts: Record<string, Record<string, number>> = {};
      // v17: per-episode cover thumbnail for the Studio grid. Best servable image
      // asset (latest version, storage_path present), scored so the designed
      // thumbnail/hook still wins over an incidental mid-scene frame. Path is a
      // factory-renders storage key; the client prefixes RENDERS_BASE. Many fresh
      // direct-mode previews have local-only assets (no storage_path) — those
      // simply get no cover and the client renders a branded fallback.
      const covers: Record<string, string> = {};
      const coverScore: Record<string, number> = {};
      const rank = (assetKey: string): number => {
        const k = assetKey.toLowerCase();
        if (k.includes("thumb") || k.includes("cover")) return 4;
        if (k.includes("hook")) return 3;
        if (k.includes("endcard") || k.includes("outro")) return 1;
        if (k.includes("frame") || k.includes("still") || k.includes("scene")) return 2;
        return 2;
      };
      const ids = (items ?? []).map((i) => i.id);
      if (ids.length > 0) {
        const { data: assets, error: aErr } = await db.from("factory_assets")
          .select("calendar_id, asset_key, version, status, kind, storage_path")
          .in("calendar_id", ids);
        if (aErr) return json({ error: aErr.message }, 500);
        const latest = new Map<string, {
          calendar_id: string; asset_key: string; version: number; status: string;
          kind: string | null; storage_path: string | null;
        }>();
        for (const a of assets ?? []) {
          const key = a.calendar_id + ":" + a.asset_key;
          const cur = latest.get(key);
          if (!cur || a.version > cur.version) latest.set(key, a);
        }
        for (const a of latest.values()) {
          const c = counts[a.calendar_id] ?? (counts[a.calendar_id] = {
            total: 0, queued: 0, generating: 0, review: 0, approved: 0, skipped: 0, failed: 0,
          });
          c.total += 1;
          if (a.status in c) c[a.status] += 1;
          // cover candidate: only images we can actually serve
          if (a.kind === "image" && a.storage_path) {
            const s = rank(a.asset_key);
            if (s > (coverScore[a.calendar_id] ?? -1)) {
              coverScore[a.calendar_id] = s;
              covers[a.calendar_id] = a.storage_path;
            }
          }
        }
      }
      // v16: a direct-mode item whose produce_preview job is still queued/running
      // but hasn't pushed its first asset yet must ALSO surface — otherwise the
      // user clicks "Produce preview" and can't find the in-flight episode in the
      // Studio list for the first few minutes (the exact confusion this closes).
      const activeDirect = new Set<string>();
      const directIds = (items ?? [])
        .filter((it) => it.production_mode === "direct").map((it) => it.id);
      if (directIds.length > 0) {
        const { data: pj, error: pErr } = await db.from("factory_jobs")
          .select("meta, status").eq("type", "produce_preview")
          .in("status", ["queued", "running"]);
        if (pErr) return json({ error: pErr.message }, 500);
        for (const j of (pj ?? [])) {
          const cid = (j.meta as Record<string, unknown> | null)?.calendar_id;
          if (typeof cid === "string" && directIds.includes(cid)) {
            activeDirect.add(cid);
            counts[cid] = counts[cid] ?? {
              total: 0, queued: 0, generating: 0, review: 0, approved: 0, skipped: 0, failed: 0,
            };
          }
        }
      }
      // hide direct-mode calendar items that have no assets AND no in-flight
      // preview job — those are plain unstarted rows, not production. Staged
      // items are included regardless (their plan_assets job creates assets soon).
      const visibleItems = (items ?? []).filter((it) =>
        it.production_mode === "staged" ||
        (counts[it.id]?.total ?? 0) > 0 ||
        activeDirect.has(it.id)
      );
      return json({ items: visibleItems, counts, covers });
    }

    // v8: one staged episode — item + every asset version + its staged jobs
    case "episode_assets": {
      const calendarId = url.searchParams.get("calendar_id");
      if (!calendarId || !UUID_RE.test(calendarId)) {
        return json({ error: "calendar_id (uuid) required" }, 400);
      }
      const [item, assets, jobs, provenance, blocksUsed, beatReview] = await Promise.all([
        db.from("factory_calendar").select("*").eq("id", calendarId).maybeSingle(),
        db.from("factory_assets").select("*").eq("calendar_id", calendarId)
          .order("created_at", { ascending: false }),
        // error + meta are load-bearing for the board: the format step shows WHY a
        // run stopped (an account cap reads very differently from a real fault),
        // and meta.iteration drives the incubation revision counter. logs +
        // heartbeat_at + started_at feed the live produce panel: the current
        // activity line, the "is it still alive?" pulse, and the elapsed timer.
        db.from("factory_jobs").select("id, type, status, title, created_at, error, meta, model, logs, heartbeat_at, started_at")
          // v16: also surface the monolithic preview job + its finalize
          // (shell_script) job so the direct-mode board can show their status
          // and gate the Finalize & Arm button.
          .in("type", [...STAGED_JOB_TYPES, "produce_preview", "shell_script"])
          .eq("meta->>calendar_id", calendarId)
          .order("created_at", { ascending: false }),
        // Cast reconciliation: what the build ACTUALLY resolved per slot
        // (factory_episode_assets_used), so the produced piece can be diffed
        // against its locked cast and a silent host/outro swap is legible.
        db.from("factory_episode_assets_used")
          .select("asset_type, version_id, build_ref, resolved_from, build_tag, created_at")
          .eq("calendar_id", calendarId)
          .order("created_at", { ascending: false }),
        // S4 · block reconciliation — the SEQUENCE twin of the cast provenance
        // above: which block played at each position per build
        // (factory_episode_blocks_used), so the produced piece can be diffed
        // against its locked composition._sequence and a silent block drop/swap
        // is legible. Non-critical (bookkeeping) like provenance — degrade to [].
        db.from("factory_episode_blocks_used")
          .select("position, block_type, layout, ref, rendered, resolved_from, build_tag, created_at")
          .eq("calendar_id", calendarId)
          .order("created_at", { ascending: false }),
        // S5 · per-beat REVIEW state (factory_episode_beat_review) — swap/regen/
        // confidence/notes the operator set per scene. Non-critical + additive like
        // the two provenance reads above: degrade to [] so the board keeps working
        // if migration 025 hasn't applied yet (deploy-order safe).
        db.from("factory_episode_beat_review")
          .select("position, block_ref, swap_asset_key, regen_kind, confidence, note, updated_at")
          .eq("calendar_id", calendarId)
          .order("position", { ascending: true }),
      ]);
      const err = item.error || assets.error || jobs.error;
      if (err) return json({ error: err.message }, 500);
      if (!item.data) return json({ error: "calendar item not found" }, 404);
      // S5 · generation manifest rides on the calendar row (select * above), so no
      // second version-row select — one-select resolve stays intact. null until the
      // build composes it, which keeps the classic path byte-identical.
      return json({ item: item.data, assets: assets.data, jobs: jobs.data,
                    provenance: provenance.data || [],
                    sequence: blocksUsed.data || [],
                    manifest: item.data.generation_manifest ?? null,
                    beat_review: beatReview.data || [] });
    }

    case "events": {
      const limit = clampLimit(url.searchParams.get("limit"), 50, 500);
      const { data, error } = await db.from("factory_events").select("*")
        .order("ts", { ascending: false }).limit(limit);
      if (error) return json({ error: error.message }, 500);
      return json({ events: data });
    }

    // v14: worker registry. Derives online/offline from last_seen (online =
    // seen within WORKER_ONLINE_S) and reports each worker's current running
    // load so the dashboard can show live status. job_types is the full set of
    // routable types for the routing UI.
    case "workers": {
      const WORKER_ONLINE_S = 90;
      const [workers, running, settings] = await Promise.all([
        db.from("factory_workers").select("*").order("registered_at", { ascending: true }),
        db.from("factory_jobs").select("assigned_worker").eq("status", "running"),
        // v13: global model/effort override (applies to ALL workers/jobs)
        db.from("factory_settings").select("key, value")
          .in("key", ["override_enabled", "override_model", "override_effort", "worker_paused"]),
      ]);
      if (workers.error) return json({ error: workers.error.message }, 500);
      const load: Record<string, number> = {};
      for (const j of (running.data ?? [])) {
        const w = (j as { assigned_worker: string | null }).assigned_worker;
        if (w) load[w] = (load[w] ?? 0) + 1;
      }
      const now = Date.now();
      // deno-lint-ignore no-explicit-any
      const rows = (workers.data ?? []).map((w: any) => ({
        ...w,
        running: load[w.worker_id] ?? 0,
        online: w.last_seen ? (now - new Date(w.last_seen).getTime()) < WORKER_ONLINE_S * 1000 : false,
      }));
      const s: Record<string, string> = {};
      for (const row of (settings.data ?? [])) s[row.key] = row.value;
      const override = {
        enabled: (s.override_enabled ?? "0") === "1",
        model: s.override_model ?? null,
        effort: s.override_effort ?? null,
      };
      return json({
        workers: rows,
        job_types: JOB_TYPES,
        override,
        global_paused: (s.worker_paused ?? "0") === "1",
      });
    }

    // v15: worker log lines pushed by each machine during heartbeat
    case "worker_logs": {
      const wid = url.searchParams.get("worker_id");
      if (!wid) return json({ error: "worker_id required" }, 400);
      const limit = Math.min(200, parseInt(url.searchParams.get("limit") ?? "80", 10));
      const { data, error } = await db.from("factory_worker_logs")
        .select("ts, level, message")
        .eq("worker_id", wid)
        .order("ts", { ascending: false })
        .limit(limit);
      if (error) return json({ error: error.message }, 500);
      return json({ logs: (data ?? []).reverse() });
    }

    default:
      return json({ error: "unknown resource: " + (r ?? "(none)") }, 400);
  }
}

// deno-lint-ignore no-explicit-any
async function handlePost(body: any): Promise<Response> {
  switch (body.action) {
    case "create_channel": {
      const { key, name, niche, accent, guidelines } = body;
      if (!key || !name) return json({ error: "key and name required" }, 400);
      const { data, error } = await db.from("factory_channels")
        .insert({
          key,
          name,
          niche: niche ?? null,
          accent: accent ?? null,
          guidelines: guidelines ?? "",
          status: "active",
        })
        .select().single();
      if (error) {
        return json({ error: error.message }, error.code === "23505" ? 409 : 500);
      }
      await logEvent("channel_created", `Channel '${name}' (${key}) created`, { key });
      return json({ channel: data });
    }

    case "update_channel": {
      const { key, patch } = body;
      if (!key || !patch || typeof patch !== "object") {
        return json({ error: "key and patch required" }, 400);
      }
      const allowed = ["name", "niche", "accent", "guidelines", "status", "brand", "lifecycle", "baseline_ref", "template"];
      const clean: Record<string, unknown> = {};
      for (const k of allowed) if (k in patch) clean[k] = patch[k];
      if (Object.keys(clean).length === 0) {
        return json({ error: "patch has no updatable fields" }, 400);
      }
      const { data, error } = await db.from("factory_channels")
        .update(clean).eq("key", key).select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "channel not found" }, 404);
      return json({ channel: data });
    }

    case "create_job": {
      const { channel_key, type, title, prompt, model, effort, ultracode } = body;
      if (!channel_key || !type) return json({ error: "channel_key and type required" }, 400);
      if (!JOB_TYPES.includes(type)) {
        return json({ error: "type must be one of: " + JOB_TYPES.join(" | ") }, 400);
      }
      if (effort !== undefined && !EFFORTS.includes(effort)) {
        return json({ error: "effort must be one of: " + EFFORTS.join(" | ") }, 400);
      }
      const row: Record<string, unknown> = {
        channel_key,
        type,
        title: title ?? null,
        prompt: prompt ?? null,
        status: "queued",
      };
      if (model !== undefined) row.model = model;
      if (effort !== undefined) row.effort = effort;
      if (ultracode !== undefined) row.ultracode = Boolean(ultracode);
      if (body.target_worker) row.target_worker = body.target_worker;  // v14: optional per-job pin
      const { data, error } = await db.from("factory_jobs").insert(row).select().single();
      if (error) return json({ error: error.message }, 500);
      await logEvent("job_created", `Job '${data.title ?? data.type}' queued for ${channel_key}`, {
        job_id: data.id,
        channel_key,
        type,
      });
      return json({ job: data });
    }

    case "cancel_job": {
      const { id } = body;
      if (!id) return json({ error: "id required" }, 400);
      const { data, error } = await db.from("factory_jobs")
        .update({ status: "cancelled", finished_at: new Date().toISOString() })
        .eq("id", id).eq("status", "queued")
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "job not found or not queued" }, 409);
      await logEvent("job_cancelled", `Job ${id} cancelled`, { job_id: id });
      return json({ job: data });
    }

    // v7: request cooperative termination of a RUNNING job. Sets control='stop';
    // the worker's heartbeat loop reads it back (~4s) and terminates the claude
    // child, marking the job 'cancelled'. Only valid while status='running' —
    // queued jobs are cancelled via cancel_job instead.
    case "stop_job": {
      const { id } = body;
      if (!id) return json({ error: "id required" }, 400);
      const { data, error } = await db.from("factory_jobs")
        .update({ control: "stop" })
        .eq("id", id).eq("status", "running")
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "job not found or not running" }, 409);
      await logEvent("stop_requested", `Stop requested for job '${data.title ?? data.type}'`, {
        job_id: id,
        channel_key: data.channel_key,
      });
      return json({ job: data });
    }

    // v14: edit a worker's dashboard-owned routing config. Accepts any of:
    //   name (string), paused (bool), accept_types (string[]|null = all types),
    //   max_parallel (int, advisory). worker_id is required and must exist.
    case "update_worker": {
      const { worker_id } = body;
      if (!worker_id) return json({ error: "worker_id required" }, 400);
      const patch: Record<string, unknown> = {};
      if (body.name !== undefined) patch.name = body.name;
      if (body.paused !== undefined) patch.paused = Boolean(body.paused);
      if (body.max_parallel !== undefined) patch.max_parallel = body.max_parallel;
      if (body.accept_types !== undefined) {
        // null / [] => accept ALL types; else validate each against JOB_TYPES
        const at = body.accept_types;
        if (at !== null && !Array.isArray(at)) return json({ error: "accept_types must be an array or null" }, 400);
        if (Array.isArray(at)) {
          const bad = at.filter((t: string) => !JOB_TYPES.includes(t));
          if (bad.length) return json({ error: "unknown job types: " + bad.join(", ") }, 400);
        }
        patch.accept_types = (Array.isArray(at) && at.length) ? at : null;
      }
      if (Object.keys(patch).length === 0) return json({ error: "nothing to update" }, 400);
      const { data, error } = await db.from("factory_workers")
        .update(patch).eq("worker_id", worker_id).select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "worker not found" }, 404);
      await logEvent("worker_updated", `Worker '${data.name ?? worker_id}' updated`, { worker_id, patch });
      return json({ worker: data });
    }

    // v14: pin (or unpin) a QUEUED job to a specific worker. target_worker=null clears it.
    case "assign_job": {
      const { id, target_worker } = body;
      if (!id) return json({ error: "id required" }, 400);
      const { data, error } = await db.from("factory_jobs")
        .update({ target_worker: target_worker || null })
        .eq("id", id).eq("status", "queued")
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "job not found or not queued" }, 409);
      await logEvent("job_assigned", `Job ${id} pinned to ${target_worker || "any worker"}`,
        { job_id: id, target_worker: target_worker || null });
      return json({ job: data });
    }

    // v13: global model/effort override. When enabled, EVERY job (on every
    // worker) runs with this model/effort instead of the one it was queued with.
    // Body: { enabled: bool, model?: string, effort?: string }.
    case "set_override": {
      if (body.effort !== undefined && body.effort !== null && !EFFORTS.includes(body.effort)) {
        return json({ error: "effort must be one of: " + EFFORTS.join(" | ") }, 400);
      }
      const rows = [{ key: "override_enabled", value: body.enabled ? "1" : "0" }];
      if (body.model !== undefined) rows.push({ key: "override_model", value: body.model || "" });
      if (body.effort !== undefined) rows.push({ key: "override_effort", value: body.effort || "" });
      const { error } = await db.from("factory_settings")
        .upsert(rows, { onConflict: "key" });
      if (error) return json({ error: error.message }, 500);
      await logEvent("override_set",
        body.enabled
          ? `Global override ON -> model=${body.model ?? "(unchanged)"} effort=${body.effort ?? "(unchanged)"}`
          : "Global override OFF",
        { enabled: !!body.enabled, model: body.model ?? null, effort: body.effort ?? null });
      return json({ override: { enabled: !!body.enabled, model: body.model ?? null, effort: body.effort ?? null } });
    }

    // v14: global pause of ALL workers (worker_paused='1' short-circuits every claim).
    case "global_pause": {
      const val = body.paused ? "1" : "0";
      const { error } = await db.from("factory_settings")
        .upsert([{ key: "worker_paused", value: val }], { onConflict: "key" });
      if (error) return json({ error: error.message }, 500);
      await logEvent("global_pause", body.paused ? "ALL workers paused" : "ALL workers resumed",
        { paused: !!body.paused });
      return json({ global_paused: !!body.paused });
    }

    case "create_calendar_item": {
      const { channel_key, planned_date, title, brief, type, model, effort, ultracode } = body;
      if (!channel_key || !planned_date || !title) {
        return json({ error: "channel_key, planned_date and title required" }, 400);
      }
      if (type !== undefined && !CALENDAR_TYPES.includes(type)) {
        return json({ error: "type must be one of: " + CALENDAR_TYPES.join(" | ") }, 400);
      }
      if (effort !== undefined && !EFFORTS.includes(effort)) {
        return json({ error: "effort must be one of: " + EFFORTS.join(" | ") }, 400);
      }
      const row: Record<string, unknown> = {
        channel_key,
        planned_date,
        title,
        brief: brief ?? "",
        status: "planned",
        origin: "manual",
      };
      if (type !== undefined) row.type = type;
      if (model !== undefined) row.model = model;
      if (effort !== undefined) row.effort = effort;
      if (ultracode !== undefined) row.ultracode = Boolean(ultracode);
      const { data, error } = await db.from("factory_calendar").insert(row).select().single();
      if (error) return json({ error: error.message }, 500);
      await logEvent(
        "calendar_item_created",
        `Calendar item '${title}' planned for ${channel_key} on ${planned_date}`,
        { item_id: data.id, channel_key, planned_date },
      );
      return json({ item: data });
    }

    case "update_calendar_item": {
      const { id, patch } = body;
      if (!id || !patch || typeof patch !== "object") {
        return json({ error: "id and patch required" }, 400);
      }
      const allowed = ["planned_date", "title", "brief", "type", "model", "effort", "ultracode", "status", "auto_mode"];
      const clean: Record<string, unknown> = {};
      for (const k of allowed) if (k in patch) clean[k] = patch[k];
      if (Object.keys(clean).length === 0) {
        return json({ error: "patch has no updatable fields" }, 400);
      }
      if ("status" in clean && !CALENDAR_PATCH_STATUSES.includes(clean.status as string)) {
        return json(
          { error: "status must be one of: " + CALENDAR_PATCH_STATUSES.join(" | ") },
          400,
        );
      }
      if ("type" in clean && !CALENDAR_TYPES.includes(clean.type as string)) {
        return json({ error: "type must be one of: " + CALENDAR_TYPES.join(" | ") }, 400);
      }
      if ("effort" in clean && !EFFORTS.includes(clean.effort as string)) {
        return json({ error: "effort must be one of: " + EFFORTS.join(" | ") }, 400);
      }
      if ("ultracode" in clean) clean.ultracode = Boolean(clean.ultracode);
      const { data, error } = await db.from("factory_calendar")
        .update(clean).eq("id", id).select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "calendar item not found" }, 404);
      return json({ item: data });
    }

    case "queue_calendar_item": {
      const { id } = body;
      if (!id) return json({ error: "id required" }, 400);
      const { data: item, error: itemErr } = await db.from("factory_calendar")
        .select("*").eq("id", id).maybeSingle();
      if (itemErr) return json({ error: itemErr.message }, 500);
      if (!item) return json({ error: "calendar item not found" }, 404);
      if (item.status === "queued" || item.status === "produced") {
        return json({ error: `calendar item already ${item.status}` }, 409);
      }
      // staged-only (2026-08-07): producing an item always plans it in stages (Studio),
      // never a direct produce_short. Idempotent — refuse if it already has staged assets.
      const { count: qAssetCount, error: qAcErr } = await db.from("factory_assets")
        .select("id", { count: "exact", head: true }).eq("calendar_id", id);
      if (qAcErr) return json({ error: qAcErr.message }, 500);
      if ((qAssetCount ?? 0) > 0) {
        return json({ error: "calendar item already has staged assets — open its Studio board instead" }, 409);
      }
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key: item.channel_key,
          type: "plan_assets",
          title: "Plan assets — " + item.title,
          prompt: item.brief,
          model: item.model,
          effort: item.effort,
          ultracode: item.ultracode,
          status: "queued",
          meta: { calendar_id: item.id },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      const { data: updated, error: updErr } = await db.from("factory_calendar")
        .update({ status: "queued", production_mode: "staged", job_id: job.id })
        .eq("id", id).select().single();
      if (updErr) return json({ error: updErr.message }, 500);
      await logEvent(
        "assets_staged",
        `Staged production queued for '${item.title}' (${item.channel_key})`,
        { item_id: id, job_id: job.id, channel_key: item.channel_key },
      );
      return json({ item: updated, job });
    }

    // v6: accept a challenger suggestion — atomically (single pg transaction)
    // queue it as a job (same mechanics as queue_calendar_item), mark the
    // ORIGINAL item 'superseded', and flip the suggestion to 'queued'+job_id.
    case "supersede_calendar_item": {
      const { suggestion_id } = body;
      if (!suggestion_id || !UUID_RE.test(String(suggestion_id))) {
        return json({ error: "suggestion_id (uuid) required" }, 400);
      }
      type Row = Record<string, unknown>;
      const conn = await pgPool.connect();
      const tx = conn.createTransaction("supersede_calendar_item");
      try {
        await tx.begin();
        const sugRes = await tx.queryObject<{ row: Row }>({
          text: "select to_jsonb(c) as row from public.factory_calendar c where c.id = $1 for update",
          args: [suggestion_id],
        });
        const sug = sugRes.rows[0]?.row;
        if (!sug) {
          await tx.rollback();
          return json({ error: "suggestion not found" }, 404);
        }
        if (!sug.replaces_id) {
          await tx.rollback();
          return json({ error: "suggestion has no replaces_id (not a challenger)" }, 400);
        }
        if (sug.status !== "suggested") {
          await tx.rollback();
          return json({ error: "suggestion is not 'suggested' (status: " + sug.status + ")" }, 409);
        }
        const origRes = await tx.queryObject<{ row: Row }>({
          text: "select to_jsonb(c) as row from public.factory_calendar c where c.id = $1 for update",
          args: [sug.replaces_id],
        });
        const orig = origRes.rows[0]?.row;
        if (!orig) {
          await tx.rollback();
          return json({ error: "original calendar item not found" }, 404);
        }
        if (orig.status === "queued" || orig.status === "produced") {
          await tx.rollback();
          return json({
            error: "original item already " + orig.status +
              " — the suggestion can only be queued standalone via queue_calendar_item",
          }, 409);
        }
        // staged-only (2026-08-07): a superseded challenger is planned in stages too.
        const jobRes = await tx.queryObject<{ row: Row }>({
          text: `insert into public.factory_jobs
                   (channel_key, type, title, prompt, model, effort, ultracode, status, meta)
                 values ($1, 'plan_assets', $2, $3, $4, $5, $6, 'queued', $7::jsonb)
                 returning to_jsonb(factory_jobs) as row`,
          args: [
            sug.channel_key,
            "Plan assets — " + sug.title,
            sug.brief,
            sug.model,
            sug.effort,
            sug.ultracode,
            JSON.stringify({ calendar_id: sug.id }),
          ],
        });
        const job = jobRes.rows[0].row;
        const origUpd = await tx.queryObject<{ row: Row }>({
          text: `update public.factory_calendar set status = 'superseded'
                 where id = $1 returning to_jsonb(factory_calendar) as row`,
          args: [orig.id],
        });
        const sugUpd = await tx.queryObject<{ row: Row }>({
          text: `update public.factory_calendar set status = 'queued', production_mode = 'staged', job_id = $2
                 where id = $1 returning to_jsonb(factory_calendar) as row`,
          args: [sug.id, job.id],
        });
        await tx.commit();
        await logEvent(
          "supersede",
          `Challenger '${sug.title}' superseded '${orig.title}' and was queued as a job for ${sug.channel_key}`,
          {
            suggestion_id: sug.id,
            original_id: orig.id,
            job_id: job.id,
            channel_key: sug.channel_key,
          },
        );
        return json({
          suggestion: sugUpd.rows[0].row,
          original: origUpd.rows[0].row,
          job,
        });
      } catch (e) {
        try {
          await tx.rollback();
        } catch {
          // transaction already closed
        }
        return json({ error: e instanceof Error ? e.message : String(e) }, 500);
      } finally {
        conn.release();
      }
    }

    // v6: dismiss a challenger suggestion (original stays as-is)
    case "dismiss_challenge": {
      const { suggestion_id } = body;
      if (!suggestion_id || !UUID_RE.test(String(suggestion_id))) {
        return json({ error: "suggestion_id (uuid) required" }, 400);
      }
      const { data: sug, error: sErr } = await db.from("factory_calendar")
        .select("*").eq("id", suggestion_id).maybeSingle();
      if (sErr) return json({ error: sErr.message }, 500);
      if (!sug) return json({ error: "suggestion not found" }, 404);
      if (!sug.replaces_id) {
        return json({ error: "suggestion has no replaces_id (not a challenger)" }, 400);
      }
      if (sug.status !== "suggested") {
        return json({ error: "suggestion is not 'suggested' (status: " + sug.status + ")" }, 409);
      }
      const { data, error } = await db.from("factory_calendar")
        .update({ status: "skipped" })
        .eq("id", suggestion_id).eq("status", "suggested")
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "suggestion not found or not 'suggested'" }, 409);
      await logEvent(
        "challenge_dismissed",
        `Challenger '${data.title}' dismissed for ${data.channel_key}`,
        { suggestion_id: data.id, original_id: data.replaces_id, channel_key: data.channel_key },
      );
      return json({ item: data });
    }

    case "sync_analytics": {
      const { data: existing, error: existErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "analytics_sync")
        .in("status", ["queued", "running"]).limit(1);
      if (existErr) return json({ error: existErr.message }, 500);
      if (existing && existing.length > 0) {
        return json({ error: "an analytics_sync job is already " + existing[0].status }, 409);
      }
      // Respect global model/effort override; fall back to sonnet/low (analytics
      // is background intelligence, not creative work -- no need for heavy models).
      const { data: settingsRows } = await db.from("factory_settings").select("key, value")
        .in("key", ["override_enabled", "override_model", "override_effort"]);
      const sv: Record<string, string> = {};
      for (const r of (settingsRows ?? [])) sv[r.key] = r.value;
      const overrideOn = (sv.override_enabled ?? "0") === "1";
      const syncModel  = overrideOn && sv.override_model  ? sv.override_model  : "sonnet";
      const syncEffort = overrideOn && sv.override_effort ? sv.override_effort : "low";
      const { data: job, error } = await db.from("factory_jobs")
        .insert({
          channel_key: "_network",
          type: "analytics_sync",
          title: "Analytics sync + AI suggestions",
          model: syncModel,
          effort: syncEffort,
          status: "queued",
        })
        .select().single();
      if (error) return json({ error: error.message }, 500);
      await logEvent("analytics_sync_queued", "Analytics sync + AI suggestions job queued", {
        job_id: job.id,
      });
      return json({ job });
    }

    // v4: patch a post's YouTube metadata (only while draft/armed)
    case "update_post": {
      const { id, patch } = body;
      if (!id || !patch || typeof patch !== "object") {
        return json({ error: "id and patch required" }, 400);
      }
      const clean: Record<string, unknown> = {};
      for (const k of POST_PATCH_FIELDS) if (k in patch) clean[k] = patch[k];
      if (Object.keys(clean).length === 0) {
        return json({ error: "patch has no updatable fields" }, 400);
      }
      if ("synthetic" in clean) clean.synthetic = Boolean(clean.synthetic);
      clean.updated_at = new Date().toISOString();
      const { data, error } = await db.from("factory_posts")
        .update(clean).eq("id", id).in("status", ["draft", "armed"])
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "post not found or not editable (draft/armed only)" }, 409);
      return json({ post: data });
    }

    // v4: arm a draft post for upload (needs yt_title + future publish_at)
    case "arm_post": {
      const { id } = body;
      if (!id) return json({ error: "id required" }, 400);
      const { data: post, error: pErr } = await db.from("factory_posts")
        .select("*").eq("id", id).maybeSingle();
      if (pErr) return json({ error: pErr.message }, 500);
      if (!post) return json({ error: "post not found" }, 404);
      if (post.status !== "draft") {
        return json({ error: "post is not draft (status: " + post.status + ")" }, 409);
      }
      if (!post.yt_title || String(post.yt_title).trim() === "") {
        return json({ error: "yt_title must be nonempty to arm" }, 400);
      }
      if (!post.publish_at || new Date(post.publish_at).getTime() <= Date.now()) {
        return json({ error: "publish_at must be set and in the future to arm" }, 400);
      }
      const { data, error } = await db.from("factory_posts")
        .update({ status: "armed", updated_at: new Date().toISOString() })
        .eq("id", id).eq("status", "draft")
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "post not found or not draft" }, 409);
      await logEvent("post_armed", `Post '${data.yt_title}' armed for ${data.publish_at}`, {
        post_id: id,
        channel_key: data.channel_key,
      });
      return json({ post: data });
    }

    // v4: disarm an armed post back to draft
    // v4.1: also rescues failed posts (failed -> draft, clearing error) so they
    // can be edited and re-armed from the dashboard
    case "disarm_post": {
      const { id } = body;
      if (!id) return json({ error: "id required" }, 400);
      const { data, error } = await db.from("factory_posts")
        .update({ status: "draft", error: null, updated_at: new Date().toISOString() })
        .eq("id", id).in("status", ["armed", "failed"])
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "post not found or not armed/failed" }, 409);
      await logEvent("post_disarmed", `Post '${data.yt_title}' disarmed`, {
        post_id: id,
        channel_key: data.channel_key,
      });
      return json({ post: data });
    }

    // v4: queue a brief-suggestion job (client polls ?r=job&id= until done;
    // job result JSON contains {title, brief, tags})
    case "suggest_brief": {
      const { channel_key, seed } = body;
      if (!channel_key) return json({ error: "channel_key required" }, 400);
      const { data: job, error } = await db.from("factory_jobs")
        .insert({
          channel_key,
          type: "suggest_brief",
          model: "sonnet",
          effort: "medium",
          title: "Brief suggestion: " + channel_key,
          prompt: seed || "",
          status: "queued",
        })
        .select().single();
      if (error) return json({ error: error.message }, 500);
      await logEvent("suggest_brief_queued", "Brief suggestion job queued for " + channel_key, {
        job_id: job.id,
        channel_key,
      });
      return json({ job });
    }

    // v8: staged production — queue a plan_assets job instead of producing directly
    case "stage_calendar_item": {
      const { id } = body;
      if (!id || !UUID_RE.test(String(id))) return json({ error: "id (uuid) required" }, 400);
      return await stageCalendarItem(String(id));
    }

    // v19: accept a research-backed suggestion from the Studio shelf.
    //
    // stage_calendar_item already accepts `suggested`, but it stages the row AS
    // STORED. The shelf lets the owner edit the prefilled title/brief first, so
    // this patches then delegates to the EXACT same stage path — same guards
    // (planned|suggested → else 409; 0 assets → else 409), same plan_assets job
    // with meta.calendar_id, same {item, job} response. No fork.
    // Bind a piece to a specific locked CAST before producing. The board's
    // "Confirm the format" step could show the template but not change it, so an
    // accepted suggestion was stuck with the channel default. build_ep_v2 already
    // binds via factory_calendar.template_version_id — this just exposes it.
    case "set_calendar_template_version": {
      const { calendar_id: cvCal, template_version_id: cvVer } = body;
      if (!cvCal || !UUID_RE.test(String(cvCal))) return json({ error: "calendar_id (uuid) required" }, 400);
      if (cvVer !== null && !UUID_RE.test(String(cvVer ?? ""))) {
        return json({ error: "template_version_id must be a uuid or null" }, 400);
      }
      const { data: cvItem, error: cvItemErr } = await db.from("factory_calendar")
        .select("id, channel_key").eq("id", String(cvCal)).maybeSingle();
      if (cvItemErr) return json({ error: cvItemErr.message }, 500);
      if (!cvItem) return json({ error: "calendar item not found" }, 404);
      if (cvVer) {
        // only a LOCKED cast of the SAME channel may be bound — a draft is still
        // being edited and must never drive a render (same rule as _tpl_lookup).
        const { data: cvTv, error: cvTvErr } = await db.from("factory_template_versions")
          .select("id, status, channel_key, version, label").eq("id", String(cvVer)).maybeSingle();
        if (cvTvErr) return json({ error: cvTvErr.message }, 500);
        if (!cvTv) return json({ error: "template version not found" }, 404);
        if (cvTv.status !== "locked") {
          return json({ error: "only a locked cast can be produced with — lock it first" }, 409);
        }
        if (cvTv.channel_key !== cvItem.channel_key) {
          return json({ error: "that cast belongs to another channel" }, 409);
        }
      }
      const { data: cvUpd, error: cvUpdErr } = await db.from("factory_calendar")
        .update({ template_version_id: cvVer ?? null }).eq("id", String(cvCal)).select().single();
      if (cvUpdErr) return json({ error: cvUpdErr.message }, 500);
      return json({ ok: true, item: cvUpd });
    }

    case "accept_suggestion": {
      const { id, title, brief } = body;
      if (!id || !UUID_RE.test(String(id))) return json({ error: "id (uuid) required" }, 400);
      const patch: Record<string, unknown> = {};
      if (typeof title === "string" && title.trim()) patch.title = title.trim();
      if (typeof brief === "string") patch.brief = brief;
      // Accepting a suggestion approves the IDEA onto the calendar. It must not
      // also choose the production path: staging here forced production_mode
      // 'staged', which skips the board's "Confirm the format" step — the only
      // place the template/cast is chosen — so an accepted suggestion could not
      // switch templates. Promote suggested -> planned and let the board decide
      // (produce_preview for direct channels, stage for staged ones), exactly as
      // it does for any other planned row.
      patch.status = "planned";
      const { data: accepted, error: accErr } = await db.from("factory_calendar")
        .update(patch).eq("id", String(id)).select().single();
      if (accErr) return json({ error: accErr.message }, 500);
      if (!accepted) return json({ error: "calendar item not found" }, 404);
      await logEvent(
        "suggestion_accepted",
        `Accepted '${accepted.title}' (${accepted.channel_key}) onto the calendar`,
        { calendar_id: accepted.id },
      );
      return json({ item: accepted, job: null });
    }

    // v16: add_asset — used by scripts/push_asset.py in a produce_preview
    // session. Monolithic Claude jobs push each generated asset to the DB as
    // it lands on disk so Studio's filmstrip populates live. Auto-approved
    // (v1 asset from a monolithic pipeline is factory-QC'd inline, not
    // reviewed) — reviewer sees the preview MP4 in Studio, not per-asset.
    case "add_asset": {
      const {
        calendar_id, asset_key, group_key, kind,
        filename, local_path, size_bytes, duration_s, title,
      } = body;
      if (!calendar_id || !UUID_RE.test(String(calendar_id))) {
        return json({ error: "calendar_id (uuid) required" }, 400);
      }
      if (!asset_key || typeof asset_key !== "string") {
        return json({ error: "asset_key (string) required" }, 400);
      }
      if (!kind || !["image", "video", "audio", "text", "other"].includes(kind)) {
        return json({ error: "kind must be one of image|video|audio|text|other" }, 400);
      }
      // verify parent exists
      const { data: cal, error: cErr } = await db.from("factory_calendar")
        .select("id, channel_key").eq("id", calendar_id).maybeSingle();
      if (cErr) return json({ error: cErr.message }, 500);
      if (!cal) return json({ error: "calendar item not found" }, 404);
      // dedup by (calendar_id, asset_key) — v1 only; monolithic path doesn't revise
      const { data: existing } = await db.from("factory_assets")
        .select("id, version").eq("calendar_id", calendar_id).eq("asset_key", asset_key)
        .order("version", { ascending: false }).limit(1);
      if (existing && existing.length > 0) {
        return json({
          asset: existing[0],
          note: "already recorded, dedup by (calendar_id, asset_key)",
        });
      }
      // position auto-increments across the calendar's assets
      const { data: countRow } = await db.from("factory_assets")
        .select("id", { count: "exact", head: true }).eq("calendar_id", calendar_id);
      const position = ((countRow as unknown as { count?: number } | null)?.count ?? 0) + 1;
      const { data: inserted, error: iErr } = await db.from("factory_assets")
        .insert({
          calendar_id,
          channel_key: cal.channel_key,
          asset_key,
          version: 1,
          group_key: group_key || "other",
          kind,
          title: title || asset_key,
          status: "approved",
          filename: filename || null,
          local_path: local_path || null,
          size_bytes: size_bytes ?? null,
          duration_s: duration_s ?? null,
          position,
          spec: { prompt: "", params: {}, revision_notes: [] },
        }).select().single();
      if (iErr) return json({ error: iErr.message }, 500);
      await logEvent("asset_pushed",
        `Asset '${asset_key}' pushed from produce_preview session`,
        { asset_id: inserted.id, calendar_id, channel_key: cal.channel_key });
      return json({ asset: inserted });
    }

    // v8: approve the latest version of an asset (review → approved)
    case "approve_asset": {
      const { id } = body;
      if (!id || !UUID_RE.test(String(id))) return json({ error: "id (uuid) required" }, 400);
      const { data: asset, error: aErr } = await db.from("factory_assets")
        .select("*").eq("id", id).maybeSingle();
      if (aErr) return json({ error: aErr.message }, 500);
      if (!asset) return json({ error: "asset not found" }, 404);
      const latest = await isLatestAssetVersion(asset);
      if (latest.error) return json({ error: latest.error }, 500);
      if (!latest.latest) {
        return json({ error: `asset '${asset.asset_key}' v${asset.version} is not the latest version` }, 409);
      }
      if (asset.status !== "review") {
        return json({ error: "asset is not in review (status: " + asset.status + ")" }, 409);
      }
      const { data, error } = await db.from("factory_assets")
        .update({ status: "approved", updated_at: new Date().toISOString() })
        .eq("id", id).eq("status", "review")
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "asset not found or not in review" }, 409);
      await logEvent("asset_approved", `Asset '${asset.asset_key}' v${asset.version} approved`, {
        asset_id: id,
        calendar_id: asset.calendar_id,
        channel_key: asset.channel_key,
      });
      return json({ asset: data });
    }

    // v8: request a new version — old row superseded, new queued row + generate_asset job
    case "revise_asset": {
      const { id, notes, model, effort } = body;
      if (!id || !UUID_RE.test(String(id))) return json({ error: "id (uuid) required" }, 400);
      if (!notes || String(notes).trim() === "") return json({ error: "notes required" }, 400);
      if (effort !== undefined && !EFFORTS.includes(effort)) {
        return json({ error: "effort must be one of: " + EFFORTS.join(" | ") }, 400);
      }
      const { data: asset, error: aErr } = await db.from("factory_assets")
        .select("*").eq("id", id).maybeSingle();
      if (aErr) return json({ error: aErr.message }, 500);
      if (!asset) return json({ error: "asset not found" }, 404);
      const latest = await isLatestAssetVersion(asset);
      if (latest.error) return json({ error: latest.error }, 500);
      if (!latest.latest) {
        return json({ error: `asset '${asset.asset_key}' v${asset.version} is not the latest version` }, 409);
      }
      if (!["review", "approved", "failed"].includes(asset.status)) {
        return json({ error: "asset cannot be revised (status: " + asset.status + ")" }, 409);
      }
      const { data: pending, error: pendErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "generate_asset")
        .eq("meta->>calendar_id", asset.calendar_id)
        .eq("meta->>asset_key", asset.asset_key)
        .in("status", ["queued", "running"]).limit(1);
      if (pendErr) return json({ error: pendErr.message }, 500);
      if (pending && pending.length > 0) {
        return json({
          error: `a generation job for '${asset.asset_key}' is already ${pending[0].status} — wait for it to finish`,
        }, 409);
      }
      const { data: item, error: itemErr } = await db.from("factory_calendar")
        .select("*").eq("id", asset.calendar_id).maybeSingle();
      if (itemErr) return json({ error: itemErr.message }, 500);
      if (!item) return json({ error: "calendar item not found" }, 404);
      const version = asset.version + 1;
      const spec = { ...(asset.spec ?? {}) };
      spec.revision_notes = [
        ...(Array.isArray(spec.revision_notes) ? spec.revision_notes : []),
        { ts: new Date().toISOString(), notes: String(notes) },
      ];
      const { data: newAsset, error: insErr } = await db.from("factory_assets")
        .insert({
          calendar_id: asset.calendar_id,
          channel_key: asset.channel_key,
          asset_key: asset.asset_key,
          version,
          group_key: asset.group_key,
          kind: asset.kind,
          title: asset.title,
          spec,
          status: "queued",
          position: asset.position ?? 0,
          notes: String(notes),
          model: model ?? asset.model,
          effort: effort ?? asset.effort,
        })
        .select().single();
      if (insErr) return json({ error: insErr.message }, 500);
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key: asset.channel_key,
          type: "generate_asset",
          title: `Asset: ${asset.asset_key} v${version} — ${item.title}`,
          prompt:
            `Regenerate asset '${asset.asset_key}' v${version} — the worker builds the real prompt from the factory_assets row.`,
          model: newAsset.model,
          effort: newAsset.effort,
          status: "queued",
          meta: {
            calendar_id: asset.calendar_id,
            asset_id: newAsset.id,
            asset_key: asset.asset_key,
            version,
          },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      const { data: linked, error: linkErr } = await db.from("factory_assets")
        .update({ job_id: job.id }).eq("id", newAsset.id).select().single();
      if (linkErr) return json({ error: linkErr.message }, 500);
      // supersede LAST: if any insert above failed, the old row is untouched and the
      // board stays actionable (latest-version rule makes the old row inert either way)
      await db.from("factory_assets")
        .update({ status: "superseded", updated_at: new Date().toISOString() })
        .eq("id", id).in("status", ["review", "approved", "failed"]);
      await logEvent(
        "asset_revision",
        `Revision v${version} of '${asset.asset_key}' queued for '${item.title}'`,
        {
          asset_id: newAsset.id,
          calendar_id: asset.calendar_id,
          job_id: job.id,
          channel_key: asset.channel_key,
        },
      );
      return json({ asset: linked, job });
    }

    // v8: skip an asset (latest version, queued|review|failed) — cancels its queued job
    case "skip_asset": {
      const { id } = body;
      if (!id || !UUID_RE.test(String(id))) return json({ error: "id (uuid) required" }, 400);
      const { data: asset, error: aErr } = await db.from("factory_assets")
        .select("*").eq("id", id).maybeSingle();
      if (aErr) return json({ error: aErr.message }, 500);
      if (!asset) return json({ error: "asset not found" }, 404);
      const latest = await isLatestAssetVersion(asset);
      if (latest.error) return json({ error: latest.error }, 500);
      if (!latest.latest) {
        return json({ error: `asset '${asset.asset_key}' v${asset.version} is not the latest version` }, 409);
      }
      if (!["queued", "review", "failed"].includes(asset.status)) {
        return json({ error: "asset cannot be skipped (status: " + asset.status + ")" }, 409);
      }
      const { data, error } = await db.from("factory_assets")
        .update({ status: "skipped", updated_at: new Date().toISOString() })
        .eq("id", id).in("status", ["queued", "review", "failed"])
        .select().maybeSingle();
      if (error) return json({ error: error.message }, 500);
      if (!data) return json({ error: "asset not found or no longer skippable" }, 409);
      if (asset.job_id) {
        const { error: cancelErr } = await db.from("factory_jobs")
          .update({ status: "cancelled", finished_at: new Date().toISOString() })
          .eq("id", asset.job_id).eq("status", "queued");
        if (cancelErr) return json({ error: cancelErr.message }, 500);
      }
      await logEvent("asset_skipped", `Asset '${asset.asset_key}' v${asset.version} skipped`, {
        asset_id: id,
        calendar_id: asset.calendar_id,
        channel_key: asset.channel_key,
      });
      return json({ asset: data });
    }

    // v10: low-res DRAFT preview of the whole episode, before assembly — allowed
    // while revisions are still in review (the draft is how you judge them)
    case "queue_preview": {
      const { calendar_id } = body;
      if (!calendar_id || !UUID_RE.test(String(calendar_id))) {
        return json({ error: "calendar_id (uuid) required" }, 400);
      }
      const { data: item, error: itemErr } = await db.from("factory_calendar")
        .select("*").eq("id", calendar_id).maybeSingle();
      if (itemErr) return json({ error: itemErr.message }, 500);
      if (!item) return json({ error: "calendar item not found" }, 404);
      const { data: assets, error: aErr } = await db.from("factory_assets")
        .select("asset_key, version, status").eq("calendar_id", calendar_id);
      if (aErr) return json({ error: aErr.message }, 500);
      if (!assets || assets.length === 0) {
        return json({ error: "no assets staged for this calendar item yet" }, 409);
      }
      const latest = new Map<string, { asset_key: string; version: number; status: string }>();
      for (const a of assets) {
        const cur = latest.get(a.asset_key);
        if (!cur || a.version > cur.version) latest.set(a.asset_key, a);
      }
      const busy = [...latest.values()]
        .filter((a) => ["queued", "generating", "failed"].includes(a.status))
        .map((a) => a.asset_key);
      if (busy.length > 0) {
        return json({
          error: "not ready for a draft — " + busy.length +
            " asset(s) still generating or failed: " + busy.join(", "),
        }, 409);
      }
      const usable = [...latest.values()]
        .filter((a) => a.status === "approved" || a.status === "review").length;
      if (usable === 0) {
        return json({ error: "every asset was skipped — nothing to preview" }, 409);
      }
      const { data: existing, error: existErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "preview_episode")
        .eq("meta->>calendar_id", calendar_id)
        .in("status", ["queued", "running"]).limit(1);
      if (existErr) return json({ error: existErr.message }, 500);
      if (existing && existing.length > 0) {
        return json({ error: "a draft preview for this item is already " + existing[0].status }, 409);
      }
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key: item.channel_key,
          type: "preview_episode",
          title: "Draft preview — " + item.title,
          prompt: item.brief,
          model: item.model,
          effort: "medium",
          status: "queued",
          meta: { calendar_id },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      await logEvent(
        "preview_queued",
        `Draft preview queued for '${item.title}' (${usable} asset(s))`,
        { item_id: calendar_id, job_id: job.id, channel_key: item.channel_key },
      );
      return json({ job });
    }

    // v8: every latest version approved/skipped → queue the final assembly job
    case "queue_assembly": {
      const { calendar_id } = body;
      if (!calendar_id || !UUID_RE.test(String(calendar_id))) {
        return json({ error: "calendar_id (uuid) required" }, 400);
      }
      const { data: item, error: itemErr } = await db.from("factory_calendar")
        .select("*").eq("id", calendar_id).maybeSingle();
      if (itemErr) return json({ error: itemErr.message }, 500);
      if (!item) return json({ error: "calendar item not found" }, 404);
      const { data: assets, error: aErr } = await db.from("factory_assets")
        .select("asset_key, version, status").eq("calendar_id", calendar_id);
      if (aErr) return json({ error: aErr.message }, 500);
      if (!assets || assets.length === 0) {
        return json({ error: "no assets staged for this calendar item yet" }, 409);
      }
      const latest = new Map<string, { asset_key: string; version: number; status: string }>();
      for (const a of assets) {
        const cur = latest.get(a.asset_key);
        if (!cur || a.version > cur.version) latest.set(a.asset_key, a);
      }
      const pending = [...latest.values()]
        .filter((a) => a.status !== "approved" && a.status !== "skipped")
        .map((a) => a.asset_key);
      if (pending.length > 0) {
        return json({
          error: "not ready to assemble — " + pending.length +
            " asset(s) still need review: " + pending.join(", "),
        }, 409);
      }
      const approved = [...latest.values()].filter((a) => a.status === "approved").length;
      if (approved === 0) {
        return json({ error: "every asset was skipped — nothing to assemble" }, 409);
      }
      const { data: existing, error: existErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "assemble_episode")
        .eq("meta->>calendar_id", calendar_id)
        .in("status", ["queued", "running"]).limit(1);
      if (existErr) return json({ error: existErr.message }, 500);
      if (existing && existing.length > 0) {
        return json({ error: "an assembly job for this item is already " + existing[0].status }, 409);
      }
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key: item.channel_key,
          type: "assemble_episode",
          title: "Assemble — " + item.title,
          prompt: item.brief,
          model: item.model,
          effort: item.effort,
          status: "queued",
          meta: { calendar_id },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      await logEvent(
        "assembly_queued",
        `Assembly queued for '${item.title}' (${approved} approved asset(s))`,
        { item_id: calendar_id, job_id: job.id, channel_key: item.channel_key },
      );
      return json({ job });
    }

    // v16: produce a claude-tricks Short via the MONOLITHIC preview path
    // (build_ep_v2 engine) instead of the generic v9 plan_assets fanout. One
    // produce_preview job renders an unmastered preview + pushes each asset to
    // Studio live; the human reviews the preview in the board, then finalizes
    // (below) to master + arm YouTube. Body: {calendar_id, ep}. `ep` is the
    // episode key (e.g. "12") — it names channels/claude-tricks/episodes/<ep>.v2.json
    // and is threaded to finalize via the job's meta so both agree.
    case "produce_preview": {
      const { calendar_id } = body;
      // S4 (Sprint 5) auto-mode: run all beats with minimal review. Persisted to
      // the calendar row + job.meta so the worker honours it; the ARM GATE stays a
      // human go — finalize_episode / arm_post NEVER read this flag.
      const auto_mode = body.auto_mode === true;
      let ep = body.ep === undefined || body.ep === null ? "" : String(body.ep).trim();
      if (!calendar_id || !UUID_RE.test(String(calendar_id))) {
        return json({ error: "calendar_id (uuid) required" }, 400);
      }
      const { data: item, error: itemErr } = await db.from("factory_calendar")
        .select("*").eq("id", calendar_id).maybeSingle();
      if (itemErr) return json({ error: itemErr.message }, 500);
      if (!item) return json({ error: "calendar item not found" }, 404);
      // ep auto-assigns (last armed + 1) when the client doesn't pass one, so the
      // creator never types an episode number. finalize advances the counter at
      // arm. An explicit ep is still honored (back-compat).
      if (!ep) {
        const { data: cRow } = await db.from("factory_settings")
          .select("value").eq("key", `${item.channel_key}_last_ep`).maybeSingle();
        const lastEp = parseInt(String(cRow?.value ?? "0"), 10) || 0;
        ep = String(lastEp + 1);
      }
      if (item.status === "produced") {
        return json({ error: "calendar item already produced" }, 409);
      }
      // one preview at a time per item (a retry after done/failed is fine)
      const { data: liveJobs, error: ljErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "produce_preview")
        .eq("meta->>calendar_id", calendar_id)
        .in("status", ["queued", "running"]).limit(1);
      if (ljErr) return json({ error: ljErr.message }, 500);
      if (liveJobs && liveJobs.length > 0) {
        return json({ error: "a preview job for this item is already " + liveJobs[0].status }, 409);
      }
      // S4 · deliverable #1 — stamp the active composition version at QUEUE time so
      // this calendar/Studio-driven produce reproduces the SAME locked
      // composition._sequence at finalize. finalize_episode.py re-cuts the MASTER
      // via build_ep_v2 --calendar-id, which binds rank-4 =
      // factory_calendar.template_version_id; if that column is null it falls back
      // to whatever the channel's active version is AT FINALIZE TIME — so a lock
      // swap between preview approval and finalize would arm a master built from a
      // DIFFERENT sequence than the reviewer approved. Mirrors produce_channel's
      // activeVersion stamp. Seed from item.template_version_id FIRST so an
      // existing deliberate pin is written back unchanged (a no-op equal to
      // itself) and the rank-4 divergence guard in _bind_template_version stays
      // satisfied; only a null pin is filled with the current active version.
      let activeVersionId: string | null = item.template_version_id ?? null;
      if (!activeVersionId) {
        const { data: tplChan } = await db.from("factory_channels")
          .select("template").eq("key", item.channel_key).maybeSingle();
        const tplKey = tplChan?.template ?? null;
        if (tplKey) {
          const { data: tplActive } = await db.from("factory_templates")
            .select("active_version_id").eq("key", tplKey).maybeSingle();
          activeVersionId = tplActive?.active_version_id ?? null;
        }
      }
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key: item.channel_key,
          type: "produce_preview",
          title: "Preview — " + item.title,
          prompt: item.brief,
          model: item.model,
          effort: item.effort,
          ultracode: item.ultracode,
          status: "queued",
          meta: { calendar_id: item.id, ep, template_version_id: activeVersionId, auto_mode },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      // direct mode + queued so the Studio index (?r=staged) surfaces it once
      // its first asset lands; keep job_id pointing at the preview job. The
      // template_version_id write makes the pin DURABLE on the calendar row so
      // finalize's --calendar-id resolves it (no-op when a pin was already set).
      const { data: updated, error: updErr } = await db.from("factory_calendar")
        .update({ status: "queued", production_mode: "direct", job_id: job.id,
                  template_version_id: activeVersionId, auto_mode })
        .eq("id", calendar_id).select().single();
      if (updErr) return json({ error: updErr.message }, 500);
      await logEvent(
        "preview_queued",
        `Monolithic preview queued for '${item.title}' (ep ${ep}, ${item.channel_key})`,
        { item_id: calendar_id, job_id: job.id, channel_key: item.channel_key },
      );
      return json({ item: updated, job });
    }

    // v16: finalize a preview-approved claude-tricks Short — master + LUFS QC +
    // arm YouTube — by queuing a shell_script job that runs
    // scripts/finalize_episode.py (deterministic, ~$0 Claude). The ep key is
    // pulled from the item's produce_preview job so preview + finalize + spec
    // file all agree. finalize_episode.py writes the scheduled factory_posts row
    // and flips this item to 'produced' itself (via --calendar-id). Body:
    // {calendar_id, schedule} where schedule is an ISO-8601 UTC publish time.
    case "finalize_episode": {
      const { calendar_id, schedule } = body;
      if (!calendar_id || !UUID_RE.test(String(calendar_id))) {
        return json({ error: "calendar_id (uuid) required" }, 400);
      }
      const when = new Date(String(schedule ?? ""));
      if (!schedule || isNaN(when.getTime())) {
        return json({ error: "schedule (ISO-8601 UTC publish time) required" }, 400);
      }
      if (when.getTime() <= Date.now()) {
        return json({ error: "schedule must be in the future" }, 400);
      }
      const { data: item, error: itemErr } = await db.from("factory_calendar")
        .select("*").eq("id", calendar_id).maybeSingle();
      if (itemErr) return json({ error: itemErr.message }, 500);
      if (!item) return json({ error: "calendar item not found" }, 404);
      // no YouTube arm while the channel is still incubating — lock the baseline first
      const { data: finCh, error: finChErr } = await db.from("factory_channels")
        .select("lifecycle, template").eq("key", item.channel_key).maybeSingle();
      if (finChErr) return json({ error: finChErr.message }, 500);
      if (finCh?.lifecycle === "incubating") {
        return json({ error: "this channel is incubating — lock the baseline before scheduling on YouTube" }, 409);
      }
      // ep key comes from the produce_preview job (newest for this item)
      const { data: pvJobs, error: pvErr } = await db.from("factory_jobs")
        .select("id, meta, status, created_at").eq("type", "produce_preview")
        .eq("meta->>calendar_id", calendar_id)
        .order("created_at", { ascending: false }).limit(1);
      if (pvErr) return json({ error: pvErr.message }, 500);
      const ep = pvJobs && pvJobs.length ? String((pvJobs[0].meta as Record<string, unknown> | null)?.ep ?? "").trim() : "";
      if (!ep) {
        return json({ error: "no produce_preview job with an ep key for this item — produce a preview first" }, 409);
      }
      // one finalize in flight per item
      const { data: liveFin, error: lfErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "shell_script")
        .eq("meta->>calendar_id", calendar_id)
        .in("status", ["queued", "running"]).limit(1);
      if (lfErr) return json({ error: lfErr.message }, 500);
      if (liveFin && liveFin.length > 0) {
        return json({ error: "a finalize job for this item is already " + liveFin[0].status }, 409);
      }
      const scheduleIso = when.toISOString().replace(/\.\d{3}Z$/, "Z"); // RFC3339 UTC
      // v19: finalize routing comes from the channel's TEMPLATE (factory_templates
      // row: finalize_script + finalize_tag). A template with no finalize script
      // yet (the starter templates) 409s honestly instead of running another
      // channel's script. Channels with no template keep the legacy key mapping.
      const chKey = item.channel_key;
      let scriptPath = "";
      let finTag = "";
      if (finCh?.template) {
        const { data: tpl, error: tplErr } = await db.from("factory_templates")
          .select("finalize_script, finalize_tag").eq("key", finCh.template).maybeSingle();
        if (tplErr) return json({ error: tplErr.message }, 500);
        if (tpl) {
          if (!tpl.finalize_script) {
            return json({ error: "this channel's template has no finalize pipeline yet — a deterministic finalize script needs to be added before it can arm YouTube" }, 409);
          }
          scriptPath = tpl.finalize_script;
          finTag = tpl.finalize_tag || "v2";
        }
      }
      if (!scriptPath) {
        // legacy fallback (template missing or its row was deleted)
        scriptPath = chKey === "already-happening"
          ? "scripts/finalize_already_happening.py"
          : chKey === "aashiqana"
          ? "scripts/finalize_aashiqana.py"
          : "scripts/finalize_episode.py";
        finTag = (chKey === "already-happening" || chKey === "aashiqana") ? "v3" : "v2";
      }
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key: item.channel_key,
          type: "shell_script",
          title: "Finalize & arm — " + item.title,
          status: "queued",
          meta: {
            calendar_id,
            ep,
            script_path: scriptPath,
            script_args: [
              "--ep", ep,
              "--tag", finTag,
              "--schedule", scheduleIso,
              "--calendar-id", calendar_id,
            ],
          },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      await logEvent(
        "finalize_queued",
        `Finalize + arm queued for '${item.title}' (ep ${ep}, publish ${scheduleIso})`,
        { item_id: calendar_id, job_id: job.id, channel_key: item.channel_key },
      );
      return json({ job });
    }

    // v17: produce a new episode straight from the CHANNEL page — no calendar
    // juggling, no manual ep number. Auto-assigns the next ep (last armed + 1;
    // the counter `<channel>_last_ep` advances at ARM in finalize_episode.py, so
    // abandoned drafts never burn a number), creates an internal calendar row +
    // a produce_preview job on the LOCKED Ep11/Ep12 template. Body:
    // {channel_key, title, brief, model?, effort?}.
    case "produce_channel": {
      const { channel_key } = body;
      const title = String(body.title ?? "").trim();
      const brief = String(body.brief ?? "").trim();
      if (!channel_key) return json({ error: "channel_key required" }, 400);
      if (!title) return json({ error: "title required" }, 400);
      if (!brief) return json({ error: "brief required" }, 400);
      // Incubation: while a channel is incubating the ONLY production is its Ep01
      // TEMP (refined via revise_preview, frozen via lock_baseline). A fresh
      // produce is blocked EXCEPT the incubation Ep01 itself (body.incubation),
      // which the app auto-fires once the bring-up scaffold completes. The Ep01
      // produce runs the channel's own cloned blueprint via meta.incubation.
      const incubation = body.incubation === true;
      const { data: pcCh, error: pcChErr } = await db.from("factory_channels")
        .select("lifecycle").eq("key", channel_key).maybeSingle();
      if (pcChErr) return json({ error: pcChErr.message }, 500);
      if (!pcCh) return json({ error: "channel not found" }, 404);
      if (pcCh.lifecycle === "incubating" && !incubation) {
        return json({ error: "this channel is incubating — refine Episode 1 in the Studio (Revise / Lock), don't start a new one yet" }, 409);
      }
      // SERIAL guard: one produce in flight per channel. An unarmed direct
      // episode still sitting at status='queued' (producing or awaiting finalize)
      // blocks a new one — this is what keeps the provisional ep number
      // collision-free (finish/arm or skip the current one first).
      const { data: inFlight, error: ifErr } = await db.from("factory_calendar")
        .select("id, title").eq("channel_key", channel_key)
        .eq("production_mode", "direct").eq("status", "queued").limit(1);
      if (ifErr) return json({ error: ifErr.message }, 500);
      if (inFlight && inFlight.length > 0) {
        return json({ error: `finish or arm the current episode first ('${inFlight[0].title}') — one produce at a time` }, 409);
      }
      // next ep = last armed + 1 (provisional; finalize advances the counter at arm)
      const { data: cRow } = await db.from("factory_settings")
        .select("value").eq("key", `${channel_key}_last_ep`).maybeSingle();
      const lastEp = parseInt(String(cRow?.value ?? "0"), 10) || 0;
      const nextEp = String(lastEp + 1);
      const model = body.model ?? "opus";
      const effort = body.effort ?? "medium";
      const today = new Date().toISOString().slice(0, 10);
      // Phase 4: stamp the composed CAST this episode is produced with, at queue
      // time, so a later lock swap never rewrites history and a re-cut reproduces
      // the render. null throughout = "no composed cast" = today's behavior.
      let activeVersionId: string | null = null;
      {
        const { data: tplChan } = await db.from("factory_channels")
          .select("template").eq("key", channel_key).maybeSingle();
        const tplKey = tplChan?.template ?? null;
        if (tplKey) {
          const { data: tplActive } = await db.from("factory_templates")
            .select("active_version_id").eq("key", tplKey).maybeSingle();
          activeVersionId = tplActive?.active_version_id ?? null;
        }
      }
      // internal calendar row (origin manual so it's a normal item; the user
      // manages it from the channel page + Studio, not the calendar)
      const { data: item, error: iErr } = await db.from("factory_calendar")
        .insert({
          channel_key, planned_date: today, title, brief,
          status: "queued", origin: "manual", production_mode: "direct",
          model, effort, template_version_id: activeVersionId,
        }).select().single();
      if (iErr) return json({ error: iErr.message }, 500);
      const { data: job, error: jErr } = await db.from("factory_jobs")
        .insert({
          channel_key, type: "produce_preview",
          title: "Preview — " + title, prompt: brief,
          model, effort, status: "queued",
          meta: {
            calendar_id: item.id, ep: nextEp, source: "channel_planner",
            template_version_id: activeVersionId,
            ...(incubation ? { incubation: true, iteration: 1 } : {}),
          },
        }).select().single();
      if (jErr) return json({ error: jErr.message }, 500);
      await db.from("factory_calendar").update({ job_id: job.id }).eq("id", item.id);
      await logEvent("channel_produce",
        `Ep${nextEp} produce queued for ${channel_key}: '${title}'`,
        { item_id: item.id, job_id: job.id, channel_key, ep: nextEp });
      return json({ calendar_id: item.id, job, ep: nextEp });
    }

    // ── v18: incubation loop (Phase B) ───────────────────────────────
    // A newly-created channel starts lifecycle='incubating'. Its Ep01 is
    // produced as a TEMP, refined via revise_preview (re-run the preview with
    // appended feedback), then frozen via lock_baseline (incubating→active +
    // rewrite the blueprint into the locked canonical recipe). finalize_episode
    // and a fresh produce_channel are BLOCKED until the baseline is locked — no
    // YouTube arm off an unfrozen channel.

    // revise_preview {calendar_id, feedback}: append the feedback to the item
    // brief + the produce job's meta.feedback_log[], bump meta.iteration, and
    // re-queue produce_preview on the SAME ep so the reviewer iterates Ep01 in
    // place. (factory_calendar has no meta column, so the iteration/log live on
    // the produce_preview job's meta and carry forward across revisions.)
    case "revise_preview": {
      const { calendar_id } = body;
      const feedback = String(body.feedback ?? "").trim();
      if (!calendar_id || !UUID_RE.test(String(calendar_id))) {
        return json({ error: "calendar_id (uuid) required" }, 400);
      }
      if (!feedback) return json({ error: "feedback required" }, 400);
      const { data: item, error: itemErr } = await db.from("factory_calendar")
        .select("*").eq("id", calendar_id).maybeSingle();
      if (itemErr) return json({ error: itemErr.message }, 500);
      if (!item) return json({ error: "calendar item not found" }, 404);
      // one preview at a time per item (don't stack revisions)
      const { data: liveJobs, error: ljErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "produce_preview")
        .eq("meta->>calendar_id", String(calendar_id))
        .in("status", ["queued", "running"]).limit(1);
      if (ljErr) return json({ error: ljErr.message }, 500);
      if (liveJobs && liveJobs.length > 0) {
        return json({ error: "a preview is still " + liveJobs[0].status + " — let it finish before revising" }, 409);
      }
      // carry ep + iteration + feedback_log + incubation flag from the newest
      // produce_preview job for this item
      const { data: pvJobs, error: pvErr } = await db.from("factory_jobs")
        .select("meta, created_at").eq("type", "produce_preview")
        .eq("meta->>calendar_id", String(calendar_id))
        .order("created_at", { ascending: false }).limit(1);
      if (pvErr) return json({ error: pvErr.message }, 500);
      const prevMeta = (pvJobs && pvJobs.length ? pvJobs[0].meta : null) as Record<string, unknown> | null;
      const ep = String(prevMeta?.ep ?? "").trim();
      if (!ep) {
        return json({ error: "no produce_preview job with an ep key for this item — produce it first" }, 409);
      }
      const prevIter = Number(prevMeta?.iteration ?? 1) || 1;
      const iteration = prevIter + 1;
      const prevLog = Array.isArray(prevMeta?.feedback_log) ? prevMeta!.feedback_log as unknown[] : [];
      const feedback_log = [...prevLog, { iteration, feedback, at: new Date().toISOString() }];
      const incubation = prevMeta?.incubation === undefined ? true : !!prevMeta?.incubation;
      const newBrief = `${item.brief || ""}\n\n--- Revision ${iteration} feedback ---\n${feedback}`.trim();
      // append the feedback to the brief so the next produce sees it
      const { error: upErr } = await db.from("factory_calendar")
        .update({ brief: newBrief, status: "queued", production_mode: "direct" })
        .eq("id", calendar_id);
      if (upErr) return json({ error: upErr.message }, 500);
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key: item.channel_key,
          type: "produce_preview",
          title: `Revision ${iteration} — ${item.title}`,
          prompt: newBrief,
          model: item.model,
          effort: item.effort,
          ultracode: item.ultracode,
          status: "queued",
          meta: { calendar_id, ep, iteration, feedback_log, incubation, source: "revise" },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      await db.from("factory_calendar").update({ job_id: job.id }).eq("id", calendar_id);
      await logEvent(
        "preview_revised",
        `Revision ${iteration} queued for '${item.title}' (ep ${ep}, ${item.channel_key})`,
        { item_id: calendar_id, job_id: job.id, channel_key: item.channel_key, iteration },
      );
      return json({ job, iteration });
    }

    // lock_baseline {channel_key, calendar_id}: the reviewer is happy with the
    // Ep01 TEMP — promote the channel incubating→active, record the baseline_ref
    // (the ep the recipe is frozen from) + a <key>_baseline_locked flag, and
    // queue a freeze_baseline scaffold that rewrites the blueprint into the
    // locked canonical recipe. After this, produce/finalize work normally.
    case "lock_baseline": {
      const { channel_key, calendar_id } = body;
      if (!channel_key) return json({ error: "channel_key required" }, 400);
      if (!calendar_id || !UUID_RE.test(String(calendar_id))) {
        return json({ error: "calendar_id (uuid) required" }, 400);
      }
      const { data: channel, error: chErr } = await db.from("factory_channels")
        .select("*").eq("key", channel_key).maybeSingle();
      if (chErr) return json({ error: chErr.message }, 500);
      if (!channel) return json({ error: "channel not found" }, 404);
      if (channel.lifecycle !== "incubating") {
        return json({ error: "this channel's baseline is already locked (it is " + (channel.lifecycle ?? "active") + ")" }, 409);
      }
      const { data: item, error: itemErr } = await db.from("factory_calendar")
        .select("*").eq("id", calendar_id).maybeSingle();
      if (itemErr) return json({ error: itemErr.message }, 500);
      if (!item) return json({ error: "calendar item not found" }, 404);
      if (item.channel_key !== channel_key) {
        return json({ error: "that episode belongs to a different channel" }, 400);
      }
      if (!item.preview_path) {
        return json({ error: "produce and review Episode 1 before locking the baseline" }, 409);
      }
      // ep the recipe is frozen from (newest produce_preview job for the item)
      const { data: pvJobs, error: pvErr } = await db.from("factory_jobs")
        .select("meta, created_at").eq("type", "produce_preview")
        .eq("meta->>calendar_id", String(calendar_id))
        .order("created_at", { ascending: false }).limit(1);
      if (pvErr) return json({ error: pvErr.message }, 500);
      const ep = String((pvJobs && pvJobs.length ? (pvJobs[0].meta as Record<string, unknown> | null)?.ep : "") ?? "").trim();
      if (!ep) return json({ error: "no produce_preview job with an ep key for this item" }, 409);
      // promote the channel + record the baseline
      const { data: updated, error: upErr } = await db.from("factory_channels")
        .update({ lifecycle: "active", baseline_ref: ep }).eq("key", channel_key).select().single();
      if (upErr) return json({ error: upErr.message }, 500);
      await db.from("factory_settings")
        .upsert({ key: `${channel_key}_baseline_locked`, value: ep }, { onConflict: "key" });
      // freeze the blueprint into the locked canonical recipe from the approved Ep01
      const { data: freezeJob, error: fErr } = await db.from("factory_jobs")
        .insert({
          channel_key, type: "new_channel_scaffold",
          title: "Lock baseline — " + (channel.name || channel_key),
          status: "queued", model: "opus", effort: "medium",
          meta: { phase: "freeze_baseline", channel_key, calendar_id, ep, baseline_ref: ep },
        }).select().single();
      if (fErr) return json({ error: fErr.message }, 500);
      await logEvent(
        "baseline_locked",
        `Baseline locked for '${channel.name || channel_key}' from ep ${ep} — channel is now active`,
        { channel_key, item_id: calendar_id, ep, freeze_job: freezeJob.id },
      );
      return json({ channel: updated, freeze_job: freezeJob, ep });
    }

    // Phase 1/2 — Studio "Assets" board: lock (or unlock) the production-default
    // version for a (channel, asset_type). Demotes the current lock to 'candidate',
    // promotes the chosen version to 'locked', and upserts factory_asset_locks.
    // Body: {channel_key, asset_type, version_id} — version_id null = unlock.
    // Mirrors "lock_baseline" (guarded validation + settings upsert shape).
    case "lock_asset": {
      const { channel_key, asset_type, version_id } = body;
      if (!channel_key) return json({ error: "channel_key required" }, 400);
      if (!asset_type) return json({ error: "asset_type required" }, 400);
      const now = new Date().toISOString();
      // Guard: when promoting, the target version must exist for this
      // (channel, asset_type) — so we never demote the current lock and end up
      // with nothing locked.
      if (version_id) {
        const { data: target, error: tErr } = await db.from("factory_asset_versions")
          .select("id").eq("id", version_id)
          .eq("channel_key", channel_key).eq("asset_type", asset_type).maybeSingle();
        if (tErr) return json({ error: tErr.message }, 500);
        if (!target) return json({ error: "version not found for this channel/asset_type" }, 404);
      }
      // 1) demote the currently-locked version → candidate
      const { error: demoteErr } = await db.from("factory_asset_versions")
        .update({ status: "candidate" })
        .eq("channel_key", channel_key).eq("asset_type", asset_type).eq("status", "locked");
      if (demoteErr) return json({ error: demoteErr.message }, 500);
      // 2) promote the chosen version → locked (if any)
      if (version_id) {
        const { error: promoteErr } = await db.from("factory_asset_versions")
          .update({ status: "locked" }).eq("id", version_id);
        if (promoteErr) return json({ error: promoteErr.message }, 500);
      }
      // 3) record the lock (one row per channel/asset_type); null = unlocked
      const { error: lockErr } = await db.from("factory_asset_locks")
        .upsert(
          {
            channel_key,
            asset_type,
            locked_version_id: version_id ?? null,
            locked_at: version_id ? now : null,
            updated_at: now,
          },
          { onConflict: "channel_key,asset_type" },
        );
      if (lockErr) return json({ error: lockErr.message }, 500);
      return json({ ok: true });
    }

    // retire_asset_version {version_id}
    // Shelve a library revision that pivoted out of use (e.g. component_buildclub
    // once Build Club was de-prioritised) WITHOUT deleting bytes: status='retired'
    // + retired_at=now. The composer already refuses a retired pick and the Assets
    // board renders it struck-through. Never deletes — unretire restores it. Only
    // the owner clicks this; nothing auto-retires from code.
    case "retire_asset_version": {
      const vId = String(body.version_id ?? "");
      if (!vId || !UUID_RE.test(vId)) return json({ error: "version_id (uuid) required" }, 400);
      const { data: av, error: avErr } = await db.from("factory_asset_versions")
        .select("id, channel_key, asset_type, version, status").eq("id", vId).maybeSingle();
      if (avErr) return json({ error: avErr.message }, 500);
      if (!av) return json({ error: "asset version not found" }, 404);
      const { data: updated, error: uErr } = await db.from("factory_asset_versions")
        .update({ status: "retired", retired_at: new Date().toISOString() })
        .eq("id", vId).select().single();
      if (uErr) return json({ error: uErr.message }, 500);
      await logEvent("asset_version_retired",
        `${av.asset_type} v${av.version} retired (${av.channel_key})`,
        { channel_key: av.channel_key, asset_type: av.asset_type, version_id: vId, version: av.version });
      return json({ version: updated });
    }

    // unretire_asset_version {version_id}
    // Undo of the above — restores a retired revision to 'candidate' (never to
    // 'locked'; re-locking is an explicit lock_asset). 404 if not found; never
    // deletes.
    case "unretire_asset_version": {
      const vId = String(body.version_id ?? "");
      if (!vId || !UUID_RE.test(vId)) return json({ error: "version_id (uuid) required" }, 400);
      const { data: av, error: avErr } = await db.from("factory_asset_versions")
        .select("id, channel_key, asset_type, version, status").eq("id", vId).maybeSingle();
      if (avErr) return json({ error: avErr.message }, 500);
      if (!av) return json({ error: "asset version not found" }, 404);
      const { data: updated, error: uErr } = await db.from("factory_asset_versions")
        .update({ status: "candidate", retired_at: null })
        .eq("id", vId).select().single();
      if (uErr) return json({ error: uErr.message }, 500);
      await logEvent("asset_version_unretired",
        `${av.asset_type} v${av.version} restored (${av.channel_key})`,
        { channel_key: av.channel_key, asset_type: av.asset_type, version_id: vId, version: av.version });
      return json({ version: updated });
    }

    // ── Phase 4: the Template Composer ───────────────────────────────
    // factory_templates names the PIPELINE; a template VERSION names the CAST.
    // A version is edited as join rows while `draft`, then FROZEN into its
    // `composition` jsonb at lock (build_refs COPIED, never joined) — that is
    // what makes a locked cast reproducible after the underlying rows move on.
    //
    // create_template_version {template_key, channel_key?, label?, notes?,
    //                          from_version_id?, seed_from_locks?=true}
    // Forks a new DRAFT. Seeded from `from_version_id`'s slots (verbatim copy +
    // parent_version_id), else from the channel's factory_asset_locks — so a new
    // draft starts as EXACTLY what production runs today and the owner only
    // swaps what they want to change.
    case "create_template_version": {
      const template_key = String(body.template_key ?? "").trim();
      if (!template_key) return json({ error: "template_key required" }, 400);
      const { data: tplRow, error: tplErr } = await db.from("factory_templates")
        .select("key").eq("key", template_key).maybeSingle();
      if (tplErr) return json({ error: tplErr.message }, 500);
      if (!tplRow) return json({ error: "template not found" }, 404);

      // channel: explicit, else the channel that produces with this template.
      let channel_key = String(body.channel_key ?? "").trim();
      if (!channel_key) {
        const { data: chRows, error: chErr } = await db.from("factory_channels")
          .select("key").eq("template", template_key).limit(1);
        if (chErr) return json({ error: chErr.message }, 500);
        channel_key = chRows && chRows.length > 0 ? chRows[0].key : "";
      }
      if (!channel_key) {
        return json({ error: "channel_key required — no channel produces with this template yet" }, 400);
      }

      // Seed source: another version's slots, or the channel's live locks.
      const from_version_id = body.from_version_id ? String(body.from_version_id) : null;
      if (from_version_id && !UUID_RE.test(from_version_id)) {
        return json({ error: "from_version_id must be a uuid" }, 400);
      }
      let seedRows: { asset_type: string; asset_version_id: string; position: number; note?: string }[] = [];
      // S4 · deliverable #3 — a fork must carry the composition SEQUENCE too, not
      // just the cast. Without this, forking a designed+locked version to redesign
      // it silently opens an EMPTY Sequence designer (the Sprint-3 work is lost),
      // while edit-in-place (unlock) preserves it — so fork was the broken half of
      // "boilerplate vs redesign-from-existing".
      let seedBlocks: { position: number; block_type: string; layout: string | null; config: unknown }[] = [];
      if (from_version_id) {
        const { data: base, error: bErr } = await db.from("factory_template_versions")
          .select("id, channel_key, composition").eq("id", from_version_id).maybeSingle();
        if (bErr) return json({ error: bErr.message }, 500);
        if (!base) return json({ error: "from_version_id not found" }, 404);
        if (base.channel_key !== channel_key) {
          return json({ error: "that version belongs to a different channel" }, 400);
        }
        const { data: baseSlots, error: bsErr } = await db.from("factory_template_assets")
          .select("asset_type, asset_version_id, position, note")
          .eq("template_version_id", from_version_id);
        if (bsErr) return json({ error: bsErr.message }, 500);
        seedRows = baseSlots ?? [];
        // Blocks: prefer the editable DRAFT rows — they persist even when the
        // source is locked (lock freezes into _sequence but never deletes them).
        // Fall back to the frozen composition._sequence when a locked source has
        // had its editable rows retired. Position is preserved verbatim (a fresh
        // version id keeps UNIQUE(template_version_id, position) satisfied).
        const { data: baseBlocks, error: bbErr } = await db.from("factory_template_blocks")
          .select("position, block_type, layout, config")
          .eq("template_version_id", from_version_id).order("position", { ascending: true });
        if (bbErr) return json({ error: bbErr.message }, 500);
        if (baseBlocks && baseBlocks.length > 0) {
          seedBlocks = baseBlocks.map((b) => ({
            position: b.position, block_type: b.block_type,
            layout: b.layout ?? null, config: b.config ?? {},
          }));
        } else {
          const frozenSeq = Array.isArray(base.composition?._sequence)
            ? base.composition._sequence : [];
          seedBlocks = frozenSeq
            .filter((e: Record<string, unknown>) =>
              Number.isInteger(e?.position) && typeof e?.block_type === "string")
            .map((e: Record<string, unknown>) => ({
              position: e.position as number, block_type: e.block_type as string,
              layout: (e.layout as string | null) ?? null, config: e.config ?? {},
            }));
        }
      } else if (body.seed_from_locks !== false) {
        const { data: lockRows, error: lkErr } = await db.from("factory_asset_locks")
          .select("asset_type, locked_version_id").eq("channel_key", channel_key);
        if (lkErr) return json({ error: lkErr.message }, 500);
        seedRows = (lockRows ?? [])
          .filter((l) => !!l.locked_version_id)
          .map((l) => ({
            asset_type: l.asset_type, asset_version_id: l.locked_version_id,
            position: 0, note: "seeded from the channel lock",
          }));
      }

      // version = max + 1 for this template_key. The unique(template_key, version)
      // constraint is the real arbiter — retry once on 23505 (a concurrent fork).
      let created: { id: string; version: number } | null = null;
      let lastErr = "";
      for (let attempt = 0; attempt < 2 && !created; attempt++) {
        const { data: maxRow, error: mErr } = await db.from("factory_template_versions")
          .select("version").eq("template_key", template_key)
          .order("version", { ascending: false }).limit(1);
        if (mErr) return json({ error: mErr.message }, 500);
        const nextVersion = (maxRow && maxRow.length > 0 ? maxRow[0].version : 0) + 1;
        const { data: ins, error: insErr } = await db.from("factory_template_versions")
          .insert({
            template_key, channel_key, version: nextVersion,
            label: String(body.label ?? "").trim(),
            notes: String(body.notes ?? "").trim(),
            status: "draft", composition: {},
            parent_version_id: from_version_id,
          }).select().single();
        if (insErr) {
          lastErr = insErr.message;
          if (!String(insErr.code ?? "").includes("23505")) return json({ error: insErr.message }, 500);
          continue;
        }
        created = ins;
      }
      if (!created) return json({ error: "could not allocate a version number: " + lastErr }, 409);

      if (seedRows.length > 0) {
        const { error: seedErr } = await db.from("factory_template_assets").insert(
          seedRows.map((s) => ({
            template_version_id: created!.id,
            asset_type: s.asset_type,
            asset_version_id: s.asset_version_id,
            position: s.position ?? 0,
            note: s.note ?? "",
          })),
        );
        if (seedErr) return json({ error: seedErr.message }, 500);
      }
      // S4 · deliverable #3 — seed the forked SEQUENCE (mirrors the cast seed
      // above). A fresh version id means UNIQUE(template_version_id, position)
      // holds; the new draft re-freezes its own _sequence at lock. Empty for a
      // seed_from_locks fork (no source sequence exists) — a valid blank start.
      if (seedBlocks.length > 0) {
        const { error: sbErr } = await db.from("factory_template_blocks").insert(
          seedBlocks.map((b) => ({
            template_version_id: created!.id,
            position: b.position,
            block_type: b.block_type,
            layout: b.layout,
            config: b.config ?? {},
          })),
        );
        if (sbErr) return json({ error: sbErr.message }, 500);
      }
      const { data: slots } = await db.from("factory_template_assets")
        .select("*").eq("template_version_id", created.id)
        .order("asset_type", { ascending: true }).order("position", { ascending: true });
      await logEvent("template_version_created",
        `${template_key} v${created.version} forked as a draft (${seedRows.length} slots, ${seedBlocks.length} blocks)`,
        {
          template_key, channel_key, template_version_id: created.id,
          version: created.version, from_version_id,
          seeded: seedRows.length, seeded_blocks: seedBlocks.length,
        });
      return json({ version: created, assets: slots ?? [] });
    }

    // set_template_version_asset {template_version_id, asset_type,
    //                             asset_version_id, position?=0, note?}
    // One slot pick on a DRAFT. asset_version_id:null clears the slot.
    // Returns the version's FULL slot list so the composer re-renders from one
    // response. Locked versions are immutable — that is what makes a locked cast
    // reproducible, so this refuses rather than mutating history.
    case "set_template_version_asset": {
      const tvId = String(body.template_version_id ?? "");
      const asset_type = String(body.asset_type ?? "").trim();
      if (!tvId || !UUID_RE.test(tvId)) return json({ error: "template_version_id (uuid) required" }, 400);
      if (!asset_type) return json({ error: "asset_type required" }, 400);
      const position = Number.isFinite(Number(body.position)) ? Math.max(0, parseInt(String(body.position), 10)) : 0;
      const avId = body.asset_version_id === null || body.asset_version_id === undefined
        ? null : String(body.asset_version_id);
      if (avId !== null && !UUID_RE.test(avId)) return json({ error: "asset_version_id must be a uuid or null" }, 400);

      const { data: tv, error: tvErr } = await db.from("factory_template_versions")
        .select("id, channel_key, status").eq("id", tvId).maybeSingle();
      if (tvErr) return json({ error: tvErr.message }, 500);
      if (!tv) return json({ error: "template version not found" }, 404);
      if (tv.status !== "draft") {
        return json({ error: "locked template versions are immutable — branch a new version" }, 409);
      }

      if (avId) {
        const { data: target, error: tErr } = await db.from("factory_asset_versions")
          .select("id, status, channel_key, asset_type").eq("id", avId).maybeSingle();
        if (tErr) return json({ error: tErr.message }, 500);
        if (!target) return json({ error: "revision not found" }, 404);
        // A slot accepts any revision that feeds the SAME build key: outro_sting
        // (shared sting) and outro_card_gen (per-episode question-CTA card) are
        // both substituted into `outro_src`, and the last published short used
        // the CARD. The row is still stored under the SLOT's asset_type, which is
        // what build_ep_v2 asks for — only the build_ref travels.
        const SLOT_BUILD_KEY: Record<string, string> = {
          outro_sting: "outro_src", outro_card_gen: "outro_src",
        };
        const sameSlot = target.asset_type === asset_type;
        const sameKey = !!SLOT_BUILD_KEY[asset_type] &&
          SLOT_BUILD_KEY[asset_type] === SLOT_BUILD_KEY[target.asset_type];
        if (target.channel_key !== tv.channel_key || !(sameSlot || sameKey)) {
          return json({ error: "revision not found for this channel/asset_type" }, 404);
        }
        if (target.status === "retired") {
          return json({ error: "that revision is retired — un-retire it or pick another" }, 409);
        }
        const { error: upErr } = await db.from("factory_template_assets").upsert(
          {
            template_version_id: tvId, asset_type, asset_version_id: avId, position,
            note: String(body.note ?? "").trim(),
          },
          { onConflict: "template_version_id,asset_type,position" },
        );
        if (upErr) return json({ error: upErr.message }, 500);
      } else {
        const { error: delErr } = await db.from("factory_template_assets").delete()
          .eq("template_version_id", tvId).eq("asset_type", asset_type).eq("position", position);
        if (delErr) return json({ error: delErr.message }, 500);
      }
      const { data: slots, error: sErr } = await db.from("factory_template_assets")
        .select("*").eq("template_version_id", tvId)
        .order("asset_type", { ascending: true }).order("position", { ascending: true });
      if (sErr) return json({ error: sErr.message }, 500);
      return json({ ok: true, assets: slots ?? [] });
    }

    // set_template_version_block {template_version_id, position, block_type,
    //                             layout?, config?, cookbook_id?}
    // One block in the composition SEQUENCE on a DRAFT. The spatial sibling of
    // set_template_version_asset: draft-only (a locked cast is immutable so its
    // frozen _sequence stays reproducible), upsert on the (version, position)
    // unique key, then re-select the ORDERED blocks so the designer re-renders
    // from one response. `cookbook_id` (when the block draws a cookbook b-roll)
    // is validated against the shared 13-id catalog so a typo can't survive into
    // a locked sequence — the authoritative reference still travels inside the
    // OPEN `config` (config.cookbook.id / config.slot.broll.id), which build_ep_v2
    // turns into spec.segments.
    case "set_template_version_block": {
      const bvId = String(body.template_version_id ?? "");
      if (!bvId || !UUID_RE.test(bvId)) return json({ error: "template_version_id (uuid) required" }, 400);
      const position = Number.isFinite(Number(body.position)) ? parseInt(String(body.position), 10) : NaN;
      if (!Number.isInteger(position) || position < 0) {
        return json({ error: "position (non-negative integer) required" }, 400);
      }
      const block_type = String(body.block_type ?? "").trim();
      if (!BLOCK_TYPES.has(block_type)) {
        return json({ error: "block_type must be one of: " + [...BLOCK_TYPES].join(" | ") }, 400);
      }
      const layout = body.layout === null || body.layout === undefined || String(body.layout).trim() === ""
        ? null : String(body.layout).trim();
      if (layout !== null && !LAYOUT_IDS.has(layout)) {
        return json({ error: "unknown layout '" + layout + "' — one of: " + [...LAYOUT_IDS].join(" | ") }, 400);
      }
      const cookbook_id = body.cookbook_id === null || body.cookbook_id === undefined ||
          String(body.cookbook_id).trim() === ""
        ? null : String(body.cookbook_id).trim();
      if (cookbook_id !== null && !COOKBOOK_IDS.has(cookbook_id)) {
        return json({ error: "unknown cookbook_id '" + cookbook_id + "' — one of: " + [...COOKBOOK_IDS].join(", ") }, 400);
      }
      const config = body.config && typeof body.config === "object" && !Array.isArray(body.config)
        ? body.config : {};

      const { data: bv, error: bvErr } = await db.from("factory_template_versions")
        .select("id, channel_key, template_key, status").eq("id", bvId).maybeSingle();
      if (bvErr) return json({ error: bvErr.message }, 500);
      if (!bv) return json({ error: "template version not found" }, 404);
      if (bv.status !== "draft") {
        return json({ error: "locked template versions are immutable — branch a new version" }, 409);
      }

      const { error: bUpErr } = await db.from("factory_template_blocks").upsert(
        { template_version_id: bvId, position, block_type, layout, config },
        { onConflict: "template_version_id,position" },
      );
      if (bUpErr) return json({ error: bUpErr.message }, 500);
      const { data: blocks, error: bSelErr } = await db.from("factory_template_blocks")
        .select("*").eq("template_version_id", bvId).order("position", { ascending: true });
      if (bSelErr) return json({ error: bSelErr.message }, 500);
      await logEvent("template_block_set",
        `${bv.template_key}: block ${position} = ${block_type}` +
          (cookbook_id ? ` (${cookbook_id})` : "") + (layout ? ` [${layout}]` : ""),
        {
          template_version_id: bvId, channel_key: bv.channel_key,
          position, block_type, layout, cookbook_id,
        });
      return json({ ok: true, blocks: blocks ?? [] });
    }

    // delete_template_version_block {template_version_id, position}
    // Remove one block from a DRAFT sequence; returns the ordered remainder.
    case "delete_template_version_block": {
      const dbvId = String(body.template_version_id ?? "");
      if (!dbvId || !UUID_RE.test(dbvId)) return json({ error: "template_version_id (uuid) required" }, 400);
      const dPos = Number.isFinite(Number(body.position)) ? parseInt(String(body.position), 10) : NaN;
      if (!Number.isInteger(dPos) || dPos < 0) {
        return json({ error: "position (non-negative integer) required" }, 400);
      }
      const { data: dbv, error: dbvErr } = await db.from("factory_template_versions")
        .select("id, channel_key, template_key, status").eq("id", dbvId).maybeSingle();
      if (dbvErr) return json({ error: dbvErr.message }, 500);
      if (!dbv) return json({ error: "template version not found" }, 404);
      if (dbv.status !== "draft") {
        return json({ error: "locked template versions are immutable — branch a new version" }, 409);
      }
      const { error: dDelErr } = await db.from("factory_template_blocks").delete()
        .eq("template_version_id", dbvId).eq("position", dPos);
      if (dDelErr) return json({ error: dDelErr.message }, 500);
      const { data: dBlocks, error: dSelErr } = await db.from("factory_template_blocks")
        .select("*").eq("template_version_id", dbvId).order("position", { ascending: true });
      if (dSelErr) return json({ error: dSelErr.message }, 500);
      await logEvent("template_block_deleted",
        `${dbv.template_key}: block ${dPos} removed`,
        { template_version_id: dbvId, channel_key: dbv.channel_key, position: dPos });
      return json({ ok: true, blocks: dBlocks ?? [] });
    }

    // regenerate_asset {channel_key, asset_type, from_version_id, params, label?}
    // "Generate a new one from this." The swap drawer is where you notice a pick
    // is close but the wording is wrong, so that is where the next revision gets
    // made. Queues scripts/regen_asset.py on the EXISTING shell_script job type
    // (no new worker job type, no restart): it re-runs the slot's real generator
    // with the PARENT's params plus your overrides, uploads the result and
    // registers a CANDIDATE whose parent_version_id is the revision you started
    // from. Nothing is locked and nothing is swapped — the candidate simply
    // appears in the same drawer, to be chosen deliberately.
    //
    // GENERATABLE mirrors regen_asset.py's GENERATORS table. A slot with no
    // wired generator is refused HERE with the honest reason, rather than
    // queueing a job that would exit 2 on the worker minutes later.
    case "regenerate_asset": {
      const GENERATABLE: Record<string, string[]> = { outro_card_gen: ["q", "pill"] };
      const channel_key = String(body.channel_key ?? "").trim();
      const asset_type = String(body.asset_type ?? "").trim();
      const from_version_id = String(body.from_version_id ?? "").trim();
      if (!channel_key) return json({ error: "channel_key required" }, 400);
      if (!asset_type) return json({ error: "asset_type required" }, 400);
      if (!from_version_id || !UUID_RE.test(from_version_id)) {
        return json({ error: "from_version_id (uuid) required" }, 400);
      }
      const genParams = GENERATABLE[asset_type];
      if (!genParams) {
        return json({
          error: `no generator is wired for '${asset_type}' yet — generatable slots today: ` +
            (Object.keys(GENERATABLE).join(", ") || "none"),
        }, 400);
      }
      const { data: src, error: srcErr } = await db.from("factory_asset_versions")
        .select("id, version, label, meta").eq("id", from_version_id)
        .eq("channel_key", channel_key).eq("asset_type", asset_type).maybeSingle();
      if (srcErr) return json({ error: srcErr.message }, 500);
      if (!src) return json({ error: "revision not found for this channel/asset_type" }, 404);
      // Only this generator's own params travel. regen_asset.py inherits the
      // rest from the parent, so an untouched/empty field means "keep what the
      // parent had" instead of blanking it.
      const rawParams = (body.params ?? {}) as Record<string, unknown>;
      const params: Record<string, string> = {};
      for (const p of genParams) {
        const v = rawParams[p];
        if (v !== undefined && v !== null && String(v).trim() !== "") params[p] = String(v).trim();
      }
      const label = String(body.label ?? "").trim();
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key,
          type: "shell_script",
          title: "New " + asset_type + " from v" + src.version,
          status: "queued",
          meta: {
            asset_type,
            from_version_id,
            script_path: "scripts/regen_asset.py",
            script_args: [
              "--channel", channel_key,
              "--asset-type", asset_type,
              "--from-version", from_version_id,
              "--params", JSON.stringify(params),
              "--label", label,
            ],
          },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      await logEvent(
        "asset_regen_queued",
        `New ${asset_type} revision queued from v${src.version} (${channel_key})`,
        { job_id: job.id, channel_key, asset_type, from_version_id, params },
      );
      return json({ ok: true, job_id: job.id, job });
    }

    // capture_demo {channel_key, view, theme, url?, site?, prompt?, selector?, label?}
    // "Add a real recording asset." Films a genuine screen recording of a live
    // web app in the chosen VIEW (mobile 9:16 / desktop 16:9) and THEME
    // (light / dark), then registers it as a CANDIDATE demo_clip revision — the
    // same lineage/versioning as every other asset. Queues scripts/capture_demo.py
    // on the EXISTING shell_script job type (no new worker job type, no restart),
    // which drives scripts/record_demo.py, uploads the mp4 + poster, and inserts
    // the row. Insert shape MIRRORS regenerate_asset above (columns/status/title/
    // meta convention) so the direct-mode board tracks it the same way.
    case "capture_demo": {
      const channel_key = String(body.channel_key ?? "").trim();
      const url = String(body.url ?? "").trim();
      const site = String(body.site ?? "").trim();
      const prompt = String(body.prompt ?? "").trim();
      const selector = String(body.selector ?? "").trim();
      const label = String(body.label ?? "").trim();
      const view = String(body.view ?? "mobile").trim() || "mobile";
      const theme = String(body.theme ?? "light").trim() || "light";
      if (!channel_key) return json({ error: "channel_key required" }, 400);
      if (!url && !site) return json({ error: "one of url / site is required" }, 400);
      if (view !== "mobile" && view !== "desktop") {
        return json({ error: "view must be 'mobile' or 'desktop'" }, 400);
      }
      if (theme !== "light" && theme !== "dark") {
        return json({ error: "theme must be 'light' or 'dark'" }, 400);
      }
      // exactly one target flag reaches the script (prefer url when both are set)
      const target = url ? ["--url", url] : ["--site", site];
      const selArgs = selector ? ["--selector", selector] : [];
      const { data: job, error: jobErr } = await db.from("factory_jobs")
        .insert({
          channel_key,
          type: "shell_script",
          title: "Record demo (" + view + " · " + theme + ")",
          status: "queued",
          meta: {
            asset_type: "demo_clip",
            script_path: "scripts/capture_demo.py",
            capture: { view, theme, url: url || null, site: site || null },
            script_args: [
              "--channel", channel_key,
              "--view", view,
              "--theme", theme,
              ...target,
              "--prompt", prompt || "",
              ...selArgs,
              "--label", label || "",
            ],
          },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      await logEvent(
        "demo_capture_queued",
        `Screen recording queued (${view} · ${theme}) for ${channel_key}`,
        { job_id: job.id, channel_key, view, theme, url: url || null, site: site || null },
      );
      return json({ ok: true, job_id: job.id, job });
    }

    // lock_template_version {template_version_id, make_active?=true}
    // The materialize-and-freeze step, and the ONLY place `composition` is
    // written. Copies build_ref/label/storage_path/thumb_path/version out of
    // each factory_asset_versions row so the render is reproducible even after
    // those rows are retired. `make_active` is a POINTER SWAP on
    // factory_templates.active_version_id — deliberately NOT the demote cycle
    // lock_asset runs: older locked versions stay locked and reproducible
    // forever, which is the entire point of the frozen snapshot.
    // Cast SETTINGS: behaviour that ships with the frames but is not a file.
    // outro_cta:"auto" makes Sol speak a freshly-composed CTA over the outro
    // card; a cast describing only frames did not describe what we publish.
    case "set_template_version_setting": {
      const { template_version_id: svId, name: sName, value: sValue } = body;
      if (!svId) return json({ error: "template_version_id required" }, 400);
      if (!sName) return json({ error: "name required" }, 400);
      const { data: sv, error: svErr } = await db.from("factory_template_versions")
        .select("*").eq("id", svId).maybeSingle();
      if (svErr) return json({ error: svErr.message }, 500);
      if (!sv) return json({ error: "template version not found" }, 404);
      if (sv.status !== "draft") {
        return json({ error: "locked template versions are immutable — branch a new version" }, 409);
      }
      const meta = { ...(sv.meta ?? {}) };
      const settings = { ...(meta.settings ?? {}) };
      if (sValue === null || sValue === undefined) delete settings[sName];
      else settings[sName] = sValue;
      meta.settings = settings;
      const { error: sUpErr } = await db.from("factory_template_versions")
        .update({ meta }).eq("id", svId);
      if (sUpErr) return json({ error: sUpErr.message }, 500);
      return json({ ok: true, settings });
    }

    case "lock_template_version": {
      const lvId = String(body.template_version_id ?? "");
      if (!lvId || !UUID_RE.test(lvId)) return json({ error: "template_version_id (uuid) required" }, 400);
      const { data: lv, error: lvErr } = await db.from("factory_template_versions")
        .select("*").eq("id", lvId).maybeSingle();
      if (lvErr) return json({ error: lvErr.message }, 500);
      if (!lv) return json({ error: "template version not found" }, 404);
      if (lv.status === "locked") return json({ error: "already locked — branch a new version to change the cast" }, 409);
      if (lv.status === "retired") return json({ error: "this version is retired — branch a new version" }, 409);

      const { data: slots, error: slErr } = await db.from("factory_template_assets")
        .select("*").eq("template_version_id", lvId)
        .order("asset_type", { ascending: true }).order("position", { ascending: true });
      if (slErr) return json({ error: slErr.message }, 500);
      if (!slots || slots.length === 0) {
        return json({ error: "compose at least one asset before locking" }, 409);
      }
      const slotIds = [...new Set(slots.map((s) => s.asset_version_id))];
      const { data: avRows, error: avErr } = await db.from("factory_asset_versions")
        .select("id, channel_key, asset_type, version, label, status, storage_path, thumb_path, meta")
        .in("id", slotIds);
      if (avErr) return json({ error: avErr.message }, 500);
      // deno-lint-ignore no-explicit-any
      const avById: Record<string, any> = {};
      for (const r of avRows ?? []) avById[r.id] = r;

      // deno-lint-ignore no-explicit-any
      const composition: Record<string, any> = {};
      for (const s of slots) {
        const av = avById[s.asset_version_id];
        if (!av) return json({ error: `${s.asset_type}: a picked revision no longer exists — re-pick it` }, 409);
        if (av.channel_key !== lv.channel_key) {
          return json({ error: `${s.asset_type} v${av.version} belongs to a different channel` }, 409);
        }
        if (av.status === "retired") {
          return json({ error: `${s.asset_type} v${av.version} is retired` }, 409);
        }
        const build_ref = (av.meta ?? {}).build_ref ?? null;
        if (s.position === 0 && !build_ref) {
          return json({ error: `${s.asset_type} v${av.version} has no meta.build_ref — the build cannot resolve it` }, 409);
        }
        const frozen = {
          version_id: av.id, version: av.version, build_ref,
          label: av.label ?? "", storage_path: av.storage_path ?? null,
          thumb_path: av.thumb_path ?? null,
        };
        if (s.position === 0) {
          composition[s.asset_type] = { ...composition[s.asset_type], ...frozen };
        } else {
          const slot = composition[s.asset_type] ?? {};
          composition[s.asset_type] = { ...slot, alts: [...(slot.alts ?? []), frozen] };
        }
      }
      // Sprint 2: freeze the composition SEQUENCE alongside the frozen frames.
      // build_ep_v2 turns composition._sequence into spec.segments, so the whole
      // locked cast + sequence resolves from ONE row (migration-020 one-select
      // invariant). Ships in the SAME update as _settings below.
      const { data: seqBlocks, error: seqErr } = await db.from("factory_template_blocks")
        .select("position, block_type, layout, config")
        .eq("template_version_id", lvId).order("position", { ascending: true });
      if (seqErr) return json({ error: seqErr.message }, 500);
      const _sequence = (seqBlocks ?? []).map((b) => ({
        position: b.position,
        block_type: b.block_type,
        layout: b.layout ?? null,
        config: b.config ?? {},
      }));
      const nowIso = new Date().toISOString();
      const { data: lockedRow, error: lockErr2 } = await db.from("factory_template_versions")
        // Freeze the cast SETTINGS + SEQUENCE alongside the frames. Some of what
        // ships is behaviour, not a file — outro_cta:"auto" makes Sol speak a
        // fresh CTA over the outro card; _sequence is the ordered block plan. A
        // snapshot that captured only frames would not reproduce the episode.
        // build_ep_v2.resolve_setting() reads _settings; the builder reads
        // _sequence.
        .update({
          status: "locked",
          locked_at: nowIso,
          composition: { ...composition, _settings: (lv.meta ?? {}).settings ?? {}, _sequence },
        })
        .eq("id", lvId).select().single();
      if (lockErr2) return json({ error: lockErr2.message }, 500);

      const makeActive = body.make_active !== false;
      let previous_active_version_id: string | null = null;
      if (makeActive) {
        const { data: tplBefore } = await db.from("factory_templates")
          .select("active_version_id").eq("key", lv.template_key).maybeSingle();
        previous_active_version_id = tplBefore?.active_version_id ?? null;
        const { error: actErr } = await db.from("factory_templates")
          .update({ active_version_id: lvId }).eq("key", lv.template_key);
        if (actErr) return json({ error: actErr.message }, 500);
      }
      await logEvent("template_version_locked",
        `${lv.template_key} v${lv.version} locked` + (makeActive ? " and made active" : "") +
          ` — ${Object.keys(composition).length} slots frozen`,
        {
          template_key: lv.template_key, channel_key: lv.channel_key,
          template_version_id: lvId, version: lv.version,
          make_active: makeActive, previous_active_version_id,
          slots: Object.keys(composition),
        });
      return json({ version: lockedRow, active: makeActive, previous_active_version_id });
    }

    // unlock_template_version {template_version_id, confirm_active?:bool}
    // "Edit a locked cast in place" — the counterpart to lock, and the owner's
    // ask: a locked version is not a dead end. You can go INSIDE it and update it
    // (unlock → draft → swap → re-lock), or Fork a fresh copy. This flips
    // status locked→draft and clears locked_at, then REBUILDS the editable
    // factory_template_assets join rows from the frozen `composition` — a version
    // that was created and locked may have no join rows (or stale ones), so the
    // draft editor would otherwise have nothing to swap. meta.settings is
    // restored from composition._settings so the cast setting survives the
    // round-trip. This is the ONLY action that turns a locked version editable.
    //
    // ACTIVE-CAST GUARD: if this IS the template's active_version_id, unlocking
    // leaves production with no LOCKED active cast (build_ep_v2 only resolves
    // through a locked version — a draft is ignored, so the build falls back to
    // the channel locks, or refuses) until it is re-locked. That is honest but
    // consequential, so it requires an explicit confirm_active:true; the response
    // flags was_active either way. active_version_id is left pointing at this
    // version so re-locking with make_active restores the pointer with no gap.
    case "unlock_template_version": {
      const uvId = String(body.template_version_id ?? "");
      if (!uvId || !UUID_RE.test(uvId)) return json({ error: "template_version_id (uuid) required" }, 400);
      const { data: uv, error: uvErr } = await db.from("factory_template_versions")
        .select("*").eq("id", uvId).maybeSingle();
      if (uvErr) return json({ error: uvErr.message }, 500);
      if (!uv) return json({ error: "template version not found" }, 404);
      if (uv.status !== "locked") {
        return json({ error: "only a locked version can be unlocked (status: " + uv.status + ")" }, 409);
      }

      // Is this the template's ACTIVE cast? Unlocking re-opens it as a draft and
      // production loses its locked active cast until re-lock — require confirm.
      const { data: tplActive, error: uaErr } = await db.from("factory_templates")
        .select("key, active_version_id").eq("key", uv.template_key).maybeSingle();
      if (uaErr) return json({ error: uaErr.message }, 500);
      const was_active = !!(tplActive && tplActive.active_version_id === uvId);
      if (was_active && body.confirm_active !== true) {
        return json({
          error: "this is the template's active cast — unlocking re-opens it as a draft and production falls back until you re-lock it. Pass confirm_active:true to proceed.",
          was_active: true,
          needs_confirm: true,
        }, 409);
      }

      // Rebuild the editable join rows from the frozen composition: one position-0
      // row per slot (asset_type → composition[slot].version_id), skipping the
      // _settings / _sequence pseudo-slots. Delete any existing rows first so a
      // stale/partial set does not survive alongside the rebuilt one.
      // deno-lint-ignore no-explicit-any
      const comp = (uv.composition ?? {}) as Record<string, any>;
      const rebuilt: {
        template_version_id: string; asset_type: string;
        asset_version_id: string; position: number; note: string;
      }[] = [];
      for (const [slot, val] of Object.entries(comp)) {
        if (slot === "_settings" || slot === "_sequence") continue;
        const vId = val && (val.version_id ?? null);
        if (!vId) continue;
        rebuilt.push({
          template_version_id: uvId, asset_type: slot, asset_version_id: String(vId),
          position: 0, note: "restored from the locked composition",
        });
      }
      const { error: delErr } = await db.from("factory_template_assets").delete()
        .eq("template_version_id", uvId);
      if (delErr) return json({ error: delErr.message }, 500);
      if (rebuilt.length > 0) {
        const { error: insErr } = await db.from("factory_template_assets").insert(rebuilt);
        if (insErr) return json({ error: insErr.message }, 500);
      }

      // Sprint 2: rebuild the editable block SEQUENCE from composition._sequence —
      // the counterpart to lock freezing it. Delete any existing blocks first so a
      // stale set does not survive the round-trip, then re-insert one row per
      // frozen entry.
      // deno-lint-ignore no-explicit-any
      const seqEntries: any[] = Array.isArray(comp._sequence) ? comp._sequence : [];
      const { error: bDelErr } = await db.from("factory_template_blocks").delete()
        .eq("template_version_id", uvId);
      if (bDelErr) return json({ error: bDelErr.message }, 500);
      const blockRows = seqEntries
        .filter((e) => e && Number.isInteger(e.position) && typeof e.block_type === "string")
        .map((e) => ({
          template_version_id: uvId,
          position: e.position,
          block_type: e.block_type,
          layout: e.layout ?? null,
          config: e.config ?? {},
        }));
      if (blockRows.length > 0) {
        const { error: bInsErr } = await db.from("factory_template_blocks").insert(blockRows);
        if (bInsErr) return json({ error: bInsErr.message }, 500);
      }

      // Restore cast SETTINGS onto meta.settings so the draft editor shows them
      // and the round-trip preserves behaviour (outro_cta etc.).
      const meta = { ...(uv.meta ?? {}) };
      const frozenSettings = comp._settings;
      if (frozenSettings && typeof frozenSettings === "object") {
        meta.settings = { ...(meta.settings ?? {}), ...frozenSettings };
      }

      const { data: unlocked, error: unlErr } = await db.from("factory_template_versions")
        .update({ status: "draft", locked_at: null, meta })
        .eq("id", uvId).select().single();
      if (unlErr) return json({ error: unlErr.message }, 500);

      const { data: slots } = await db.from("factory_template_assets")
        .select("*").eq("template_version_id", uvId)
        .order("asset_type", { ascending: true }).order("position", { ascending: true });
      const { data: blocks } = await db.from("factory_template_blocks")
        .select("*").eq("template_version_id", uvId).order("position", { ascending: true });
      await logEvent("template_version_unlocked",
        `${uv.template_key} v${uv.version} unlocked for in-place editing` +
          (was_active ? " (was the active cast — production falls back until re-lock)" : "") +
          ` — ${rebuilt.length} slots + ${blockRows.length} blocks restored`,
        {
          template_key: uv.template_key, channel_key: uv.channel_key,
          template_version_id: uvId, version: uv.version,
          was_active, slots: rebuilt.map((r) => r.asset_type),
        });
      return json({ version: unlocked, assets: slots ?? [], blocks: blocks ?? [], was_active });
    }

    // retire_template_version {template_version_id, undo?:bool}
    // Shelves a cast nobody should pick up again. Refuses while it is the
    // template's ACTIVE version — silently retiring the live cast is the
    // stale-asset failure in a new costume; lock/activate another one first.
    // undo restores it to 'locked' if it was ever locked, else 'draft'.
    case "retire_template_version": {
      const rvId = String(body.template_version_id ?? "");
      if (!rvId || !UUID_RE.test(rvId)) return json({ error: "template_version_id (uuid) required" }, 400);
      const { data: rv, error: rvErr } = await db.from("factory_template_versions")
        .select("*").eq("id", rvId).maybeSingle();
      if (rvErr) return json({ error: rvErr.message }, 500);
      if (!rv) return json({ error: "template version not found" }, 404);
      const undo = body.undo === true;
      if (!undo) {
        const { data: tplActive, error: taErr } = await db.from("factory_templates")
          .select("key, active_version_id").eq("key", rv.template_key).maybeSingle();
        if (taErr) return json({ error: taErr.message }, 500);
        if (tplActive && tplActive.active_version_id === rvId) {
          return json({ error: "this version is the template's active cast — lock or activate another one first" }, 409);
        }
      }
      const { data: updated, error: uErr } = await db.from("factory_template_versions")
        .update(
          undo
            ? { status: rv.locked_at ? "locked" : "draft", retired_at: null }
            : { status: "retired", retired_at: new Date().toISOString() },
        ).eq("id", rvId).select().single();
      if (uErr) return json({ error: uErr.message }, 500);
      await logEvent(undo ? "template_version_unretired" : "template_version_retired",
        `${rv.template_key} v${rv.version} ${undo ? "restored" : "retired"}`,
        { template_key: rv.template_key, template_version_id: rvId, version: rv.version });
      return json({ version: updated });
    }

    // v17: channel-page idea engine. Queues a plan_content job; the client polls
    // ?r=job&id= until done and reads job.result.ideas (ranked). Body: {channel_key}.
    case "plan_content": {
      const { channel_key } = body;
      if (!channel_key) return json({ error: "channel_key required" }, 400);
      const { data: live, error: lErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "plan_content").eq("channel_key", channel_key)
        .in("status", ["queued", "running"]).limit(1);
      if (lErr) return json({ error: lErr.message }, 500);
      if (live && live.length > 0) {
        return json({ error: "a content-ideas job is already " + live[0].status }, 409);
      }
      const { data: job, error } = await db.from("factory_jobs")
        .insert({
          channel_key, type: "plan_content",
          model: "sonnet", effort: "medium",
          title: "Content ideas: " + channel_key, status: "queued",
        })
        .select().single();
      if (error) return json({ error: error.message }, 500);
      await logEvent("plan_content_queued", "Content-ideas job queued for " + channel_key,
        { job_id: job.id, channel_key });
      return json({ job });
    }

    // v19.3: analyze competitor/reference video links and suggest a complete
    // New-Format form (FORMAT only — structure, length, packaging grammar —
    // never identity or content). Fetches public oEmbed + watch-page metadata
    // per URL, then derives archetype heuristics. Body: { urls: string[] } (≤5).
    case "analyze_reference_urls": {
      const urls = Array.isArray(body.urls) ? body.urls.map(String).slice(0, 5) : [];
      if (urls.length === 0) return json({ error: "urls (array of YouTube links) required" }, 400);
      const vid = (u: string) => {
        const m = u.match(/(?:shorts\/|watch\?v=|youtu\.be\/)([\w-]{6,20})/);
        return m ? m[1] : null;
      };
      const refs: Record<string, unknown>[] = [];
      for (const u of urls) {
        const id = vid(u);
        if (!id) { refs.push({ url: u, error: "not a recognizable YouTube link" }); continue; }
        try {
          const oe = await fetch(
            `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${id}&format=json`,
          ).then((r) => (r.ok ? r.json() : null));
          let seconds: number | null = null;
          try {
            const page = await fetch(`https://www.youtube.com/watch?v=${id}`, {
              headers: { "user-agent": "Mozilla/5.0" },
            }).then((r) => (r.ok ? r.text() : ""));
            const lm = page.match(/"lengthSeconds":"(\d+)"/);
            if (lm) seconds = parseInt(lm[1], 10);
          } catch (_e) { /* duration is best-effort */ }
          refs.push(oe
            ? { url: u, id, title: oe.title, author: oe.author_name, seconds }
            : { url: u, id, error: "video metadata not reachable" });
        } catch (_e) {
          refs.push({ url: u, id, error: "fetch failed" });
        }
      }
      const good = refs.filter((r) => !r.error) as { title: string; author: string; seconds: number | null }[];
      if (good.length === 0) return json({ refs, error: "none of the links could be read" }, 422);

      // archetype from title grammar (format signal, not content)
      const titles = good.map((r) => String(r.title || "")).join(" || ");
      const t = titles.toLowerCase();
      let archetype = "single-tip", cloneFrom = "ai-unpacked-v16",
        titlePh = "Stop ___ (Do ___ Instead)",
        briefPh = "The tip, the on-screen proof, why it'll hold attention, and any facts to verify first…";
      if (/top ?\d|best ?\d|\d+ (things|ways|tools|plugins|commands|tips|tricks|apps|sites)/i.test(t)) {
        archetype = "ranked-countdown"; cloneFrom = "kinetic-countdown-v1";
        titlePh = "Top 5 ___ That ___";
        briefPh = "The 5 items ranked, one concrete number per item, and the #1 payoff…";
      } else if (/song|music|lyric|love|romantic|♪|lofi/i.test(t)) {
        archetype = "music"; cloneFrom = "sensual-motion-v18";
        titlePh = "Song title 🥀 | mood line #shorts";
        briefPh = "Song concept + mood, the setting, the hook line…";
      } else if (/future|will|by 20\d\d|already|prediction/i.test(t)) {
        archetype = "cinematic-speculation"; cloneFrom = "cinematic-animatic-v17";
        titlePh = "You're the last generation that will ___";
        briefPh = "The topic, today's verified anchor, the +5yr leap, and 6 shot ideas…";
      }
      // validate clone target exists; fall back to the first registry row
      const { data: tpls } = await db.from("factory_templates").select("key");
      const keys = new Set((tpls ?? []).map((x: { key: string }) => x.key));
      if (!keys.has(cloneFrom)) cloneFrom = (tpls && tpls[0] && tpls[0].key) || "ai-unpacked-v16";

      const secs = good.map((r) => r.seconds).filter((s): s is number => s != null && s > 0);
      const runtime = secs.length
        ? Math.round(secs.reduce((a, b) => a + b, 0) / secs.length)
        : 30;
      const srcLine = good.map((r) => `${r.author} — “${String(r.title).slice(0, 60)}”`).join("; ");
      const suggestion = {
        name: archetype === "ranked-countdown" ? "Ranked Countdown (from reference)"
          : archetype === "music" ? "Music Short (from reference)"
          : archetype === "cinematic-speculation" ? "Cinematic Speculation (from reference)"
          : "Single-Tip Short (from reference)",
        clone_from: cloneFrom,
        runtime_s: Math.min(Math.max(runtime, 15), 60),
        description:
          `Format read from ${srcLine} (${runtime}s). ${archetype} structure with our locked ` +
          `distribution rules: proof-hook inside 2s, pattern-interrupt rhythm, loop-seam ending, ` +
          `spoken series-CTA in the last 3s, search-intent title for the tail.`,
        tag: "🧪 " + (archetype === "ranked-countdown" ? "Ranked Countdown"
          : archetype === "music" ? "Music Short"
          : archetype === "cinematic-speculation" ? "Cinematic Speculation"
          : "Single-Tip"),
        title_ph: titlePh,
        brief_ph: briefPh,
        archetype,
      };
      return json({ refs, suggestion });
    }

    // v19.2: create a template by CLONING an existing one's pipeline wiring
    // (produce/plan/finalize routing + blueprint) and overriding the creative
    // surface (name, description, runtime, produce-panel copy). Registry rows
    // are plain data, so a clone is immediately usable by the channel picker.
    // Body: { name, clone_from, description?, runtime_s?, aspect?, produce_ui?, blueprint_source? }
    case "create_template": {
      const name = String(body.name ?? "").trim();
      const cloneFrom = String(body.clone_from ?? "").trim();
      if (!name) return json({ error: "name required" }, 400);
      if (!cloneFrom) return json({ error: "clone_from (existing template key) required" }, 400);
      const { data: parent, error: pErr } = await db.from("factory_templates")
        .select("*").eq("key", cloneFrom).maybeSingle();
      if (pErr) return json({ error: pErr.message }, 500);
      if (!parent) return json({ error: "clone_from template not found" }, 404);
      const key = String(body.key ?? name).trim().toLowerCase()
        .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48);
      if (!key) return json({ error: "could not derive a key from the name" }, 400);
      const { data: row, error } = await db.from("factory_templates")
        .insert({
          key,
          name,
          description: body.description != null ? String(body.description) : parent.description,
          produce_style: parent.produce_style,
          plan_style: parent.plan_style,
          finalize_script: parent.finalize_script,
          finalize_tag: parent.finalize_tag,
          blueprint_source: body.blueprint_source != null && String(body.blueprint_source).trim()
            ? String(body.blueprint_source).trim()
            : parent.blueprint_source,
          aspect: body.aspect != null ? String(body.aspect) : parent.aspect,
          runtime_s: body.runtime_s != null ? parseInt(String(body.runtime_s), 10) || parent.runtime_s : parent.runtime_s,
          model: parent.model,
          effort: parent.effort,
          produce_ui: body.produce_ui && typeof body.produce_ui === "object"
            ? body.produce_ui
            : parent.produce_ui,
        }).select().single();
      if (error) return json({ error: error.message }, error.code === "23505" ? 409 : 500);
      await logEvent("template_created",
        `Template '${name}' (${key}) created from ${cloneFrom}`, { key, clone_from: cloneFrom });
      return json({ template: row });
    }

    // ── v18: channel-creation wizard ─────────────────────────────────
    // A draft accumulates the creator's answers step by step; each step can ask
    // the factory for AI-suggested options (wizard_suggest → channel_intake job);
    // finalize creates the channel (incubating) + queues its bring-up scaffold.

    case "create_channel_draft": {
      const seed = body.seed === undefined || body.seed === null ? null : String(body.seed);
      const { data: draft, error } = await db.from("factory_channel_drafts")
        .insert({ seed }).select().single();
      if (error) return json({ error: error.message }, 500);
      await logEvent("channel_draft_started", "Channel wizard started", { draft_id: draft.id });
      return json({ draft });
    }

    case "update_channel_draft": {
      const { draft_id } = body;
      if (!draft_id || !UUID_RE.test(String(draft_id))) {
        return json({ error: "draft_id (uuid) required" }, 400);
      }
      const { data: draft, error: dErr } = await db.from("factory_channel_drafts")
        .select("*").eq("id", draft_id).maybeSingle();
      if (dErr) return json({ error: dErr.message }, 500);
      if (!draft) return json({ error: "draft not found" }, 404);
      const answers = {
        ...((draft.answers as Record<string, unknown>) ?? {}),
        ...(body.patch && typeof body.patch === "object" ? body.patch : {}),
      };
      const transcript = Array.isArray(draft.transcript) ? [...draft.transcript] : [];
      if (body.transcript_entry) transcript.push(body.transcript_entry);
      const upd: Record<string, unknown> = {
        answers, transcript, updated_at: new Date().toISOString(),
      };
      if (typeof body.step === "number") upd.step = body.step;
      const { data: out, error } = await db.from("factory_channel_drafts")
        .update(upd).eq("id", draft_id).select().single();
      if (error) return json({ error: error.message }, 500);
      return json({ draft: out });
    }

    case "wizard_suggest": {
      const { draft_id } = body;
      const step = typeof body.step === "number"
        ? body.step
        : (body.step !== undefined && body.step !== null ? parseInt(String(body.step), 10) : NaN);
      if (!draft_id || !UUID_RE.test(String(draft_id))) {
        return json({ error: "draft_id (uuid) required" }, 400);
      }
      if (Number.isNaN(step)) return json({ error: "step (number) required" }, 400);
      // reuse an in-flight suggestion job for this draft rather than stacking them
      const { data: live, error: lErr } = await db.from("factory_jobs")
        .select("id, status").eq("type", "channel_intake")
        .eq("meta->>draft_id", String(draft_id))
        .in("status", ["queued", "running"]).limit(1);
      if (lErr) return json({ error: lErr.message }, 500);
      if (live && live.length > 0) return json({ job: live[0] });
      const { data: job, error } = await db.from("factory_jobs")
        .insert({
          channel_key: "_network", type: "channel_intake",
          model: "sonnet", effort: "medium",
          title: "Channel wizard · step " + step, status: "queued",
          meta: {
            draft_id, step,
            field: body.field ?? null,
            question: body.question ?? null,
            answers: body.answers && typeof body.answers === "object" ? body.answers : {},
          },
        }).select().single();
      if (error) return json({ error: error.message }, 500);
      return json({ job });
    }

    case "finalize_channel_draft": {
      const { draft_id } = body;
      if (!draft_id || !UUID_RE.test(String(draft_id))) {
        return json({ error: "draft_id (uuid) required" }, 400);
      }
      const { data: draft, error: dErr } = await db.from("factory_channel_drafts")
        .select("*").eq("id", draft_id).maybeSingle();
      if (dErr) return json({ error: dErr.message }, 500);
      if (!draft) return json({ error: "draft not found" }, 404);
      if (draft.created_channel_key) {
        return json({ error: "this draft already created a channel" }, 409);
      }
      const a = (draft.answers as Record<string, unknown>) ?? {};
      const key = String(a.key ?? "").trim().toLowerCase();
      const name = String(a.name ?? "").trim();
      if (!key || !name) return json({ error: "channel name and key are required before creating" }, 400);
      if (!/^[a-z0-9][a-z0-9-]*$/.test(key)) {
        return json({ error: "key must be lowercase letters, numbers and hyphens" }, 400);
      }
      // v19: the wizard's production-style answer picks a starter TEMPLATE from
      // the registry — it drives the blueprint clone at bring-up and all later
      // produce/plan/finalize routing. Order matters: "Host-less cinematic"
      // contains "host", so the host-less test runs first.
      const prod = String(a.production ?? "").toLowerCase();
      const templateKey =
        /host-?less|cinematic/.test(prod) ? "cinematic"
        : /avatar|host/.test(prod) ? "avatar-host"
        : /illustrat|baked/.test(prod) ? "baked-text"
        : /image|story|motion/.test(prod) ? "image-story"
        : "cinematic";
      const { data: tplRow } = await db.from("factory_templates")
        .select("key, produce_style, plan_style, blueprint_source")
        .eq("key", templateKey).maybeSingle();
      const { data: channel, error: cErr } = await db.from("factory_channels")
        .insert({
          key, name,
          niche: (a.niche as string) ?? null,
          accent: (a.accent as string) ?? null,
          guidelines: (a.guidelines as string) ?? "",
          brand: a,               // the captured answers ARE the machine-readable brand bible
          status: "active",
          lifecycle: "incubating",
          template: tplRow ? templateKey : null,
        }).select().single();
      if (cErr) return json({ error: cErr.message }, cErr.code === "23505" ? 409 : 500);
      // seed the episode counter so the first produce auto-assigns Ep 1
      await db.from("factory_settings")
        .upsert({ key: `${key}_last_ep`, value: "0" }, { onConflict: "key" });
      // queue the bring-up scaffold (worker writes channels/<key>/, blueprint, brand assets)
      const { data: scaffoldJob, error: sErr } = await db.from("factory_jobs")
        .insert({
          channel_key: key, type: "new_channel_scaffold",
          title: "Set up channel — " + name, status: "queued",
          model: "opus", effort: "medium",
          meta: { phase: "bringup", draft_id, brand: a, template: tplRow ?? null },
        }).select().single();
      if (sErr) return json({ error: sErr.message }, 500);
      await db.from("factory_channel_drafts")
        .update({ status: "created", created_channel_key: key, updated_at: new Date().toISOString() })
        .eq("id", draft_id);
      await logEvent("channel_created",
        `Channel '${name}' (${key}) created via wizard — incubating`,
        { key, draft_id, scaffold_job: scaffoldJob.id });
      return json({ channel, scaffold_job: scaffoldJob });
    }

    default:
      return json({ error: "unknown action: " + (body.action ?? "(none)") }, 400);
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS });
  }

  try {
    // --- auth: sha256(x-factory-token) vs factory_settings.token_sha256 ---
    const token = req.headers.get("x-factory-token");
    if (!token) return json({ error: "missing x-factory-token" }, 401);
    const hash = await sha256Hex(token);
    const { data: setting, error: settingErr } = await db.from("factory_settings")
      .select("value").eq("key", "token_sha256").maybeSingle();
    if (settingErr) return json({ error: settingErr.message }, 500);
    if (!setting?.value || setting.value !== hash) {
      return json({ error: "invalid token" }, 401);
    }

    if (req.method === "GET") {
      return await handleGet(new URL(req.url));
    }

    if (req.method === "POST") {
      let body: unknown;
      try {
        body = await req.json();
      } catch {
        return json({ error: "invalid JSON body" }, 400);
      }
      if (!body || typeof body !== "object" || typeof (body as { action?: unknown }).action !== "string") {
        return json({ error: "action required" }, 400);
      }
      return await handlePost(body);
    }

    return json({ error: "method not allowed" }, 405);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : String(e) }, 500);
  }
});
