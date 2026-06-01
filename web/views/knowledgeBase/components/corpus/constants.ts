import type { NodeType } from "./types";

export const NODE_SIZE: Record<NodeType, number> = {
  topic: 28,
  subject: 16,
  article: 8,
};

export const NODE_COLOR: Record<NodeType, string> = {
  topic: "#10b981",
  subject: "#3b82f6",
  article: "#8b5cf6",
};

/** Topic đang mở rộng (focus) — xanh dương */
export const FOCUSED_TOPIC_COLOR = "#2563eb";
/** Subject con khi topic đang focus — tím đậm, dễ nhìn */
export const FOCUSED_SUBJECT_COLOR = "#9333ea";
export const FOCUSED_SUBJECT_EDGE_COLOR = "#a855f7";

export const SELECTED_TOPIC_COLOR = FOCUSED_TOPIC_COLOR;
export const SELECTED_SUBJECT_COLOR = "#2563eb";
export const DIMMED_EDGE_COLOR = "#cbd5e1";
export const SEARCH_COLOR_PREFIX = "#f59e0b";
export const SEARCH_COLOR_CONTAINS = "#f97316";

export const TOPIC_PAGE_SIZE = 50;
export const CHILD_PAGE_SIZE = 100;
export const GRAPH_MIN_DISTANCE = 80;
export const GRAPH_MAX_DISTANCE = 50000;

export const PARTICLE_POSITIONS: [number, number][] = [
  [8, 12],
  [15, 28],
  [22, 8],
  [35, 18],
  [48, 32],
  [62, 14],
  [78, 24],
  [88, 10],
  [12, 55],
  [28, 68],
  [42, 48],
  [58, 72],
  [72, 58],
  [85, 65],
  [6, 82],
  [18, 90],
  [55, 85],
  [92, 42],
  [38, 38],
  [65, 38],
  [50, 62],
  [25, 45],
  [75, 78],
  [45, 15],
];
