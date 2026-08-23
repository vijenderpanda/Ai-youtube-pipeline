#!/usr/bin/env -S npx tsx
/* =============================================================================
   auto_compose.ts — Sprint 5 (S2): the auto-compose engine.

   Turns a SCENE LIST into a strong-first-cut DRAFT composition sequence:
     1. pickCookbook(beatIntent) per scene chooses the best-fit visual component,
        single-sourced from remotion-studio/src/cookbook/registry.ts (the ONLY
        ranking source — the edge validator carries just id/label/role/needs and
        cannot rank, so the composer runs here, in Node via tsx).
     2. each scene -> ONE draft block written through set_template_version_block —
        the only legal, server-validated write path (draft-only 409; cookbook_id
        checked vs the 17-id catalog), so a bad pick can never enter a locked seq.
     3. stamps sequence_mode (default 'replace') via set_template_version_setting,
        which lock freezes into composition._settings — realizing VJ's
        per-composition-mode decision (default 'augment' stays byte-identical).

   Each scene carries its VO script `line`. In replace mode build_ep_v2 derives
   the timeline 1:1 from those lines (one scene = one VO line = one segment dur),
   preserving the existing VO-timing machinery — see docs/DESIGNER-SPRINT-PLAN.md.

   SAFE BY DEFAULT: with no --commit it runs --dry (pickCookbook + payload build
   only, NO network) so the composition can be inspected before any write. Live
   writes need --commit + --version <draftId> + FACTORY_TOKEN (secrets/factory.env).

   Usage:
     npx tsx scripts/auto_compose.ts --scenes fixture.json --dry
     npx tsx scripts/auto_compose.ts --scenes fixture.json --version <draftId> --commit
   ========================================================================== */
import { pickCookbook, type BeatIntent } from "../remotion-studio/src/cookbook/registry";
import { readFileSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const API_BASE = "https://xfqyovimnqdghiekicqr.supabase.co/functions/v1/factory-api";
// Public anon (publishable) JWT — same value push_asset.py uses; the real gate is
// the x-factory-token header (edge deployed --no-verify-jwt).
const ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhmcXlvdmltbnFkZ2hpZWtpY3FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExMTIyMzksImV4cCI6MjA5NjY4ODIzOX0." +
  "CA_znXaUlgmChBLFSE_eRZ4X-xg2WhwIiZmxwXrZRlM";

/* A scene = one VO line + as much beat intent as the planner knows. Any intent
   field may be omitted; more fields => a sharper pickCookbook match. */
type Scene = {
  line: string; // the VO script line for this scene (drives replace-mode timing)
  beat?: BeatIntent["beat"];
  needs?: BeatIntent["needs"];
  keywords?: string[];
  role?: BeatIntent["role"];
  minWow?: number;
  transparent?: boolean;
  block_type?: string; // default 'broll' (full-frame cookbook); 'slot' for host+broll layout
  layout?: string | null; // default per block_type
  host?: Record<string, unknown>; // slot blocks only
  props?: Record<string, unknown>; // props handed to the chosen component
  dur?: number; // placeholder; replace-mode overrides from the VO
};
type SceneDoc = {
  channel_key?: string;
  template_version_id?: string;
  sequence_mode?: "replace" | "augment";
  scenes: Scene[];
};

type Block = {
  action: "set_template_version_block";
  template_version_id: string;
  position: number;
  block_type: string;
  layout: string | null;
  cookbook_id: string; // validation gate; authoritative ref also rides in config
  config: Record<string, unknown>;
};

function parseArgs(argv: string[]) {
  const a: Record<string, string | boolean> = {};
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t.startsWith("--")) {
      const k = t.slice(2);
      const nxt = argv[i + 1];
      if (nxt && !nxt.startsWith("--")) { a[k] = nxt; i++; } else { a[k] = true; }
    }
  }
  return a;
}

function loadFactoryToken(): string {
  const p = join(REPO, "secrets", "factory.env");
  let txt = "";
  try { txt = readFileSync(p, "utf8"); }
  catch { throw new Error(`secrets/factory.env not found at ${p}`); }
  for (const line of txt.split("\n")) {
    const s = line.trim();
    if (s.startsWith("FACTORY_TOKEN=")) return s.slice("FACTORY_TOKEN=".length).trim();
  }
  throw new Error("FACTORY_TOKEN not present in secrets/factory.env");
}

/* Normalize a pickCookbook score to 0..1 confidence. A strong match lands near
   5 (needs) + 3 (beat) + a few keyword hits + wow/10; ~8 is a confident fit, so
   we divide by 8 and clamp. The low-confidence REVIEW threshold (S3/S6) reads
   this number but is decided separately. */
const confidenceOf = (score: number) => Math.min(1, Math.round((score / 8) * 100) / 100);

/* Turn one scene into a draft block, choosing its component via pickCookbook.
   Matches the designer's conventions (webapp SequenceEditor DEFAULT_CONFIG):
   'broll' => full-broll + config.cookbook; 'slot' => layout + config.broll. */
function compose(scene: Scene, position: number, versionId: string): { block: Block; pick: any } {
  const intent: BeatIntent = {
    beat: scene.beat, needs: scene.needs, keywords: scene.keywords,
    role: scene.role, minWow: scene.minWow, transparent: scene.transparent,
  };
  const [top] = pickCookbook(intent, 1);
  // Never drop a scene: replace mode is 1 scene : 1 VO line, so a line that
  // matches nothing still composes — KineticQuote carries a spoken phrase — at
  // 0 confidence so the manifest/review flags it. (A hard role/minWow filter
  // that matches nothing is the operator's own constraint, so still fail there.)
  if (!top && (scene.role || scene.minWow != null || scene.transparent)) {
    throw new Error(
      `scene ${position}: no component satisfies role/minWow/transparent ` +
      `${JSON.stringify(intent)} — loosen the filter or add keywords`,
    );
  }
  const id = top ? top.entry.id : "KineticQuote";
  const confidence = top ? confidenceOf(top.score) : 0;
  const block_type = scene.block_type || "broll";
  const layout = scene.layout !== undefined
    ? scene.layout
    : (block_type === "slot" ? "host-top" : "full-broll");
  const props = scene.props || {};

  const config: Record<string, unknown> = { line: scene.line, confidence };
  if (scene.dur != null) config.dur = scene.dur;
  if (block_type === "slot") {
    config.layout = layout;
    config.host = scene.host || {};
    config.broll = { kind: "cookbook", id, props };
  } else {
    config.cookbook = { id, props };
  }

  return {
    block: { action: "set_template_version_block", template_version_id: versionId,
             position, block_type, layout, cookbook_id: id, config },
    pick: { position, id, score: top ? top.score : 0, confidence,
            why: top ? top.why : ["fallback: no keyword match"], line: scene.line },
  };
}

async function post(body: Record<string, unknown>, token: string) {
  const res = await fetch(API_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + ANON_KEY,
               "x-factory-token": token },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* non-JSON */ }
  if (!res.ok) {
    throw new Error(`${body.action} -> ${res.status}: ${(data && data.error) || text || res.statusText}`);
  }
  return data;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const scenesPath = args.scenes as string;
  if (!scenesPath) throw new Error("--scenes <path.json> required");
  const doc = JSON.parse(readFileSync(resolve(String(scenesPath)), "utf8")) as SceneDoc;
  if (!Array.isArray(doc.scenes) || doc.scenes.length === 0) throw new Error("scenes[] is empty");

  const versionId = (args.version as string) || doc.template_version_id || "";
  const mode = (args.mode as string) || doc.sequence_mode || "replace";
  if (mode !== "replace" && mode !== "augment") throw new Error(`--mode must be replace|augment (got ${mode})`);
  const commit = args.commit === true;

  // In dry mode the versionId is only echoed, so tolerate a placeholder.
  const vid = versionId || "<draft-version-id>";
  const composed = doc.scenes.map((s, i) => compose(s, i, vid));

  // --- report --------------------------------------------------------------
  console.log(`\nauto-compose · ${doc.scenes.length} scenes · sequence_mode='${mode}'` +
              (versionId ? ` · version ${versionId}` : " · (no --version)"));
  console.log("─".repeat(64));
  for (const { pick } of composed) {
    const pct = Math.round(pick.confidence * 100);
    const flag = pick.confidence < 0.5 ? "  ⚠ low" : "";
    console.log(
      `  ${String(pick.position).padStart(2)}  ${pick.id.padEnd(16)} ` +
      `score ${String(pick.score).padStart(5)}  conf ${String(pct).padStart(3)}%${flag}`);
    console.log(`      why: ${pick.why.join(", ") || "(intent-free)"}`);
    console.log(`      line: ${JSON.stringify(pick.line)}`);
  }
  console.log("─".repeat(64));

  if (!commit) {
    console.log("DRY RUN — no writes. Block payloads:");
    console.log(JSON.stringify(composed.map((c) => c.block), null, 2));
    console.log("\nRe-run with  --version <draftId> --commit  to write these to a DRAFT.");
    return;
  }

  // --- commit --------------------------------------------------------------
  if (!versionId) throw new Error("--commit needs --version <draftId> (or template_version_id in the scenes doc)");
  const token = loadFactoryToken();
  for (const { block } of composed) {
    await post(block, token);
    console.log(`  wrote block ${block.position} (${block.block_type} · ${block.cookbook_id})`);
  }
  await post({ action: "set_template_version_setting", template_version_id: versionId,
               name: "sequence_mode", value: mode }, token);
  console.log(`  stamped sequence_mode='${mode}'`);
  console.log(`\n✓ ${composed.length} blocks written to draft ${versionId}. Lock it to freeze composition._sequence.`);
}

main().catch((e) => { console.error("!! " + (e?.message || e)); process.exit(1); });
