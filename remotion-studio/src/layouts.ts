/* =============================================================================
   LAYOUT CATALOG — the named spatial arrangements a scene can use.

   The SECOND design axis (SEQUENCE × LAYOUT): a layout decides WHERE each slot
   sits on the 1080x1920 frame — host, b-roll, caption, #tag — decoupled from
   WHAT fills each slot. This is the library the designer picks from per scene;
   a scene stores a `layout` id + its slot fills, and `SlotScene` renders it.

   Legacy beat kinds (pipCallout / splitWide / framedHost / recFull) are their
   own hard-tuned layouts and keep rendering via their existing paths; the
   entries below with `native:true` name them so the designer can still offer
   them, while the `native:false` entries are the generic, slot-composed layouts.
   Rects are fractions of the frame (x,y = top-left; w,h = size).
   ========================================================================== */

export type Rect = { x: number; y: number; w: number; h: number };
export type SlotName = "broll" | "host" | "caption" | "tag";
export type CaptionZone = "band" | "low" | "panel";

export type LayoutDef = {
  id: string;
  title: string;
  slots: Partial<Record<SlotName, Rect>>;
  captionZone: CaptionZone; // where the karaoke caption sits for this layout
  native?: boolean; // true = drawn by an existing beat kind, not SlotScene
  nativeKind?: string; // the seg.kind that draws a native layout
  note?: string;
};

export const LAYOUTS: LayoutDef[] = [
  {
    id: "full-broll",
    title: "Full b-roll",
    slots: { broll: { x: 0, y: 0, w: 1, h: 1 }, tag: { x: 0.06, y: 0.06, w: 0.34, h: 0.05 } },
    captionZone: "band",
    note: "The visual fills the frame; caption in the bottom band, #tag top-left.",
  },
  {
    id: "host-top",
    title: "Host top",
    slots: { host: { x: 0.06, y: 0.05, w: 0.88, h: 0.34 }, broll: { x: 0.06, y: 0.42, w: 0.88, h: 0.42 } },
    captionZone: "band",
    note: "Host up top, the visual below — a talking intro over a graphic.",
  },
  {
    id: "host-bottom",
    title: "Host bottom",
    slots: { broll: { x: 0.06, y: 0.05, w: 0.88, h: 0.44 }, host: { x: 0.06, y: 0.52, w: 0.88, h: 0.42 } },
    captionZone: "low",
    note: "Visual on top, host below reacting to it.",
  },
  {
    id: "split",
    title: "Split",
    slots: { host: { x: 0.05, y: 0.28, w: 0.43, h: 0.44 }, broll: { x: 0.52, y: 0.28, w: 0.43, h: 0.44 } },
    captionZone: "band",
    note: "Host and visual side by side.",
  },
  {
    id: "host-pip",
    title: "Host pip",
    slots: { broll: { x: 0, y: 0, w: 1, h: 1 }, host: { x: 0.55, y: 0.62, w: 0.4, h: 0.3 } },
    captionZone: "band",
    note: "Full-frame visual with the host as a picture-in-picture.",
  },
  {
    id: "framed",
    title: "Framed host",
    slots: { host: { x: 0.08, y: 0.13, w: 0.84, h: 0.5 } },
    captionZone: "panel",
    note: 'Contained host card + a "THE IDEA" caption panel.',
    native: true,
    nativeKind: "framed",
  },
];

export const layoutById = (id: string): LayoutDef | undefined =>
  LAYOUTS.find((l) => l.id === id);
