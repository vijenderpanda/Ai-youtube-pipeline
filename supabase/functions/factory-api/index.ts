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
// v4: post fields patchable via update_post
const POST_PATCH_FIELDS = [
  "yt_title",
  "yt_description",
  "tags",
  "publish_at",
  "audience",
  "synthetic",
];
// v7: + control, heartbeat_at (job-control: stop requests + worker liveness)
const JOB_LIST_COLS =
  "id, channel_key, type, title, prompt, model, effort, status, result, error, created_at, started_at, finished_at, control, heartbeat_at, assigned_worker, target_worker";

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
      const [item, assets, jobs] = await Promise.all([
        db.from("factory_calendar").select("*").eq("id", calendarId).maybeSingle(),
        db.from("factory_assets").select("*").eq("calendar_id", calendarId)
          .order("created_at", { ascending: false }),
        db.from("factory_jobs").select("id, type, status, title, created_at")
          // v16: also surface the monolithic preview job + its finalize
          // (shell_script) job so the direct-mode board can show their status
          // and gate the Finalize & Arm button.
          .in("type", [...STAGED_JOB_TYPES, "produce_preview", "shell_script"])
          .eq("meta->>calendar_id", calendarId)
          .order("created_at", { ascending: false }),
      ]);
      const err = item.error || assets.error || jobs.error;
      if (err) return json({ error: err.message }, 500);
      if (!item.data) return json({ error: "calendar item not found" }, 404);
      return json({ item: item.data, assets: assets.data, jobs: jobs.data });
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
      const allowed = ["name", "niche", "accent", "guidelines", "status"];
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
      const allowed = ["planned_date", "title", "brief", "type", "model", "effort", "ultracode", "status"];
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
          meta: { calendar_id: item.id, ep },
        })
        .select().single();
      if (jobErr) return json({ error: jobErr.message }, 500);
      // direct mode + queued so the Studio index (?r=staged) surfaces it once
      // its first asset lands; keep job_id pointing at the preview job.
      const { data: updated, error: updErr } = await db.from("factory_calendar")
        .update({ status: "queued", production_mode: "direct", job_id: job.id })
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
      // v17: already-happening finalizes with a DIFFERENT deterministic script —
      // it gates on the human-rendered Wan 2.6 motion clips (MOTION-TODO.md
      // sentinel) then builds the real cut + arms. claude-tricks keeps its own.
      // v18: each channel finalizes with its own deterministic script.
      // aashiqana = LOCKED sensual-motion Shorts template (SHORTS-TEMPLATE-LOCKED.md):
      // LUFS-master the branded cut + arm via yt_upload (--synthetic, Music, non-kids).
      const chKey = item.channel_key;
      const scriptPath = chKey === "already-happening"
        ? "scripts/finalize_already_happening.py"
        : chKey === "aashiqana"
        ? "scripts/finalize_aashiqana.py"
        : "scripts/finalize_episode.py";
      const finTag = (chKey === "already-happening" || chKey === "aashiqana") ? "v3" : "v2";
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
      // internal calendar row (origin manual so it's a normal item; the user
      // manages it from the channel page + Studio, not the calendar)
      const { data: item, error: iErr } = await db.from("factory_calendar")
        .insert({
          channel_key, planned_date: today, title, brief,
          status: "queued", origin: "manual", production_mode: "direct",
          model, effort,
        }).select().single();
      if (iErr) return json({ error: iErr.message }, 500);
      const { data: job, error: jErr } = await db.from("factory_jobs")
        .insert({
          channel_key, type: "produce_preview",
          title: "Preview — " + title, prompt: brief,
          model, effort, status: "queued",
          meta: { calendar_id: item.id, ep: nextEp, source: "channel_planner" },
        }).select().single();
      if (jErr) return json({ error: jErr.message }, 500);
      await db.from("factory_calendar").update({ job_id: job.id }).eq("id", item.id);
      await logEvent("channel_produce",
        `Ep${nextEp} produce queued for ${channel_key}: '${title}'`,
        { item_id: item.id, job_id: job.id, channel_key, ep: nextEp });
      return json({ calendar_id: item.id, job, ep: nextEp });
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
