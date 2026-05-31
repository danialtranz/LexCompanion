"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  ArrowRight,
  Box,
  Calendar,
  Clock,
  Download,
  FileText,
  Hash,
  Home,
  Layers,
  ListOrdered,
  Loader2,
  Maximize2,
  Minimize2,
  Minus,
  Plus,
  Search,
  Sun,
  Target,
  X,
} from "lucide-react";
import {
  darkTheme,
  lightTheme,
  type GraphCanvasRef,
  type GraphEdge,
  type InternalGraphNode,
} from "reagraph";
import documentService from "@/service/documentService";
import {
  useAdminLegalSubjectDetail,
  useAdminLegalTopicDetail,
  useAdminLegalTopicsList,
  type AdminLegalArticleItem,
  type AdminLegalSubjectDetail,
  type AdminLegalTopicDetail,
  type ApiEnvelope,
  type LegalTreeNodeItem,
} from "@/hooks/useDocumentHook";
import GraphCanvas from "./LegalCorpusGraph";

type NodeType = "topic" | "subject" | "article";

type CorpusNodeData = {
  nodeType: NodeType;
  entityId: string;
  article?: AdminLegalArticleItem;
};

type ReagraphNode = {
  id: string;
  label: string;
  subLabel?: string;
  size: number;
  fill: string;
  data: CorpusNodeData;
};

type GraphState = {
  nodes: ReagraphNode[];
  edges: GraphEdge[];
};

type SelectedNode = {
  nodeType: NodeType;
  entityId: string;
  label: string;
  article?: AdminLegalArticleItem;
};

const NODE_SIZE: Record<NodeType, number> = {
  topic: 28,
  subject: 16,
  article: 8,
};

const NODE_COLOR: Record<NodeType, string> = {
  topic: "#10b981",
  subject: "#3b82f6",
  article: "#8b5cf6",
};

const SELECTED_TOPIC_COLOR = "#059669";
const SELECTED_SUBJECT_COLOR = "#2563eb";
const DIMMED_EDGE_COLOR = "#cbd5e1";
const SEARCH_COLOR_PREFIX = "#f59e0b";
const SEARCH_COLOR_CONTAINS = "#f97316";

type SearchMatchKind = "prefix" | "contains";

type SearchMatch = {
  id: string;
  label: string;
  kind: SearchMatchKind;
  nodeType: NodeType;
  entityId: string;
  article?: AdminLegalArticleItem;
};

const TOPIC_PAGE_SIZE = 50;
const CHILD_PAGE_SIZE = 100;
const GRAPH_MIN_DISTANCE = 80;
const GRAPH_MAX_DISTANCE = 50000;

const PARTICLE_POSITIONS = [
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

function buildGraphTheme(isDark: boolean) {
  const base = isDark ? darkTheme : lightTheme;
  return {
    ...base,
    canvas: {
      ...base.canvas,
      background: isDark ? "#0f172a" : "#eef2f7",
      fog: null,
    },
    node: {
      ...base.node,
      activeFill: SELECTED_TOPIC_COLOR,
      inactiveOpacity: isDark ? 0.12 : 0.18,
      label: {
        ...base.node.label,
        color: isDark ? "#e2e8f0" : "#1e293b",
        stroke: isDark ? "#0f172a" : "#ffffff",
        activeColor: SELECTED_TOPIC_COLOR,
      },
    },
    edge: {
      ...base.edge,
      fill: isDark ? "#334155" : "#cbd5e1",
      activeFill: NODE_COLOR.topic,
      opacity: isDark ? 0.5 : 0.55,
      inactiveOpacity: isDark ? 0.06 : 0.08,
    },
    ring: {
      ...base.ring,
      fill: `${NODE_COLOR.topic}33`,
      activeFill: NODE_COLOR.topic,
    },
  };
}

function nodeId(type: NodeType, entityId: string) {
  return `${type}:${entityId}`;
}

function truncateLabel(text: string, maxLen: number): string {
  const t = text.trim();
  if (t.length <= maxLen) return t;
  return `${t.slice(0, maxLen - 1)}…`;
}

function entityIdFromNodeId(id: string): string {
  return id.split(":").slice(1).join(":");
}

function mixWithGray(hex: string, amount = 0.5): string {
  const normalized = hex.replace("#", "");
  if (normalized.length !== 6) return hex;
  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  const gray = 0xd6d3d1;
  const mix = (c: number) => Math.round(c + (gray - c) * amount);
  const toHex = (n: number) => n.toString(16).padStart(2, "0");
  return `#${toHex(mix(r))}${toHex(mix(g))}${toHex(mix(b))}`;
}

function topicSubLabel(
  graph: GraphState,
  topicNodeId: string,
): string | undefined {
  const subjectIds = graph.edges
    .filter((edge) => edge.source === topicNodeId)
    .map((edge) => edge.target);
  if (subjectIds.length === 0) return undefined;

  const articleCount = subjectIds.reduce(
    (sum, subjectId) =>
      sum + graph.edges.filter((edge) => edge.source === subjectId).length,
    0,
  );

  return `${subjectIds.length} subject • ${articleCount.toLocaleString("vi-VN")} articles`;
}

function enrichGraphLabels(graph: GraphState): GraphState {
  return {
    ...graph,
    nodes: graph.nodes.map((node) => {
      if (node.data.nodeType !== "topic") return node;
      const subLabel = topicSubLabel(graph, node.id);
      return subLabel ? { ...node, subLabel } : node;
    }),
  };
}

function collapseBranch(prev: GraphState, parentNodeId: string): GraphState {
  const directChildIds = prev.edges
    .filter((edge) => edge.source === parentNodeId)
    .map((edge) => edge.target);

  const nodesToRemove = new Set<string>();
  for (const childId of directChildIds) {
    nodesToRemove.add(childId);
    prev.edges
      .filter((edge) => edge.source === childId)
      .forEach((edge) => nodesToRemove.add(edge.target));
  }

  return {
    nodes: prev.nodes.filter((node) => !nodesToRemove.has(node.id)),
    edges: prev.edges.filter(
      (edge) =>
        !nodesToRemove.has(edge.source) && !nodesToRemove.has(edge.target),
    ),
  };
}

function applyTopicFocusStyle(
  graph: GraphState,
  topicEntityId: string,
): GraphState {
  const topicNodeId = nodeId("topic", topicEntityId);
  const childSubjectIds = new Set(
    graph.edges
      .filter((edge) => edge.source === topicNodeId)
      .map((edge) => edge.target),
  );
  const focusEdgeIds = new Set(
    graph.edges
      .filter(
        (edge) =>
          edge.source === topicNodeId ||
          childSubjectIds.has(edge.source) ||
          childSubjectIds.has(edge.target),
      )
      .map((edge) => edge.id),
  );

  return {
    nodes: graph.nodes.map((node) => {
      if (node.id === topicNodeId) {
        return {
          ...node,
          fill: SELECTED_TOPIC_COLOR,
          size: NODE_SIZE.topic * 1.35,
        };
      }
      if (childSubjectIds.has(node.id)) {
        return {
          ...node,
          fill: NODE_COLOR.subject,
          size: NODE_SIZE.subject * 1.2,
        };
      }
      const nodeType = node.data.nodeType;
      return {
        ...node,
        fill: mixWithGray(NODE_COLOR[nodeType], 0.38),
        size: NODE_SIZE[nodeType] * 0.78,
      };
    }),
    edges: graph.edges.map((edge) =>
      focusEdgeIds.has(edge.id)
        ? { ...edge, fill: NODE_COLOR.subject }
        : { ...edge, fill: DIMMED_EDGE_COLOR },
    ),
  };
}

function applySubjectFocusStyle(
  graph: GraphState,
  subjectEntityId: string,
): GraphState {
  const subjectNodeId = nodeId("subject", subjectEntityId);
  const childArticleIds = new Set(
    graph.edges
      .filter(
        (edge) =>
          edge.source === subjectNodeId && edge.target.startsWith("article:"),
      )
      .map((edge) => edge.target),
  );
  const focusEdgeIds = new Set(
    graph.edges
      .filter(
        (edge) =>
          edge.source === subjectNodeId ||
          childArticleIds.has(edge.source) ||
          childArticleIds.has(edge.target),
      )
      .map((edge) => edge.id),
  );

  return {
    nodes: graph.nodes.map((node) => {
      if (node.id === subjectNodeId) {
        return {
          ...node,
          fill: SELECTED_SUBJECT_COLOR,
          size: NODE_SIZE.subject * 1.3,
        };
      }
      if (childArticleIds.has(node.id)) {
        return {
          ...node,
          fill: NODE_COLOR.article,
          size: NODE_SIZE.article * 1.15,
        };
      }
      const nodeType = node.data.nodeType;
      return {
        ...node,
        fill: mixWithGray(NODE_COLOR[nodeType], 0.38),
        size: NODE_SIZE[nodeType] * 0.78,
      };
    }),
    edges: graph.edges.map((edge) =>
      focusEdgeIds.has(edge.id)
        ? { ...edge, fill: NODE_COLOR.article }
        : { ...edge, fill: DIMMED_EDGE_COLOR },
    ),
  };
}

function normalizeSearchText(text: string): string {
  return text.trim().toLowerCase();
}

function matchSearchTitle(
  label: string,
  query: string,
): SearchMatchKind | null {
  const q = normalizeSearchText(query);
  if (!q) return null;

  const title = normalizeSearchText(label);
  if (title.startsWith(q)) return "prefix";
  if (title.includes(q)) return "contains";
  return null;
}

function findSearchMatches(
  nodes: ReagraphNode[],
  query: string,
): SearchMatch[] {
  const q = query.trim();
  if (!q) return [];

  const prefixMatches: SearchMatch[] = [];
  const containsMatches: SearchMatch[] = [];

  for (const node of nodes) {
    const kind = matchSearchTitle(node.label, q);
    if (!kind) continue;

    const match: SearchMatch = {
      id: node.id,
      label: node.label,
      kind,
      nodeType: node.data.nodeType,
      entityId: node.data.entityId,
      article: node.data.article,
    };

    if (kind === "prefix") {
      prefixMatches.push(match);
    } else {
      containsMatches.push(match);
    }
  }

  const byLabel = (a: SearchMatch, b: SearchMatch) =>
    a.label.localeCompare(b.label, "vi");

  prefixMatches.sort(byLabel);
  containsMatches.sort(byLabel);

  return [...prefixMatches, ...containsMatches];
}

function applySearchHighlight(graph: GraphState, query: string): GraphState {
  const q = query.trim();
  if (!q) return graph;

  const prefixIds = new Set<string>();
  const containsIds = new Set<string>();

  for (const node of graph.nodes) {
    const kind = matchSearchTitle(node.label, q);
    if (kind === "prefix") prefixIds.add(node.id);
    else if (kind === "contains") containsIds.add(node.id);
  }

  if (prefixIds.size === 0 && containsIds.size === 0) return graph;

  const isMatchEdge = (edge: GraphEdge) =>
    prefixIds.has(edge.source) ||
    prefixIds.has(edge.target) ||
    containsIds.has(edge.source) ||
    containsIds.has(edge.target);

  return {
    ...graph,
    nodes: graph.nodes.map((node) => {
      if (prefixIds.has(node.id)) {
        return {
          ...node,
          fill: SEARCH_COLOR_PREFIX,
          size: node.size * 1.25,
        };
      }
      if (containsIds.has(node.id)) {
        return {
          ...node,
          fill: SEARCH_COLOR_CONTAINS,
          size: node.size * 1.15,
        };
      }
      return {
        ...node,
        fill: mixWithGray(node.fill, 0.75),
        size: node.size * 0.6,
      };
    }),
    edges: graph.edges.map((edge) =>
      isMatchEdge(edge) ? edge : { ...edge, fill: DIMMED_EDGE_COLOR },
    ),
  };
}

function mergeGraph(
  prev: GraphState,
  newNodes: ReagraphNode[],
  newEdges: GraphEdge[],
): GraphState {
  const nodeMap = new Map(prev.nodes.map((n) => [n.id, n]));
  newNodes.forEach((n) => nodeMap.set(n.id, n));

  const edgeKeys = new Set(prev.edges.map((e) => e.id));
  const edges = [...prev.edges];
  newEdges.forEach((e) => {
    if (!edgeKeys.has(e.id)) {
      edgeKeys.add(e.id);
      edges.push(e);
    }
  });

  return { nodes: Array.from(nodeMap.values()), edges };
}

function topicNodesFromItems(items: LegalTreeNodeItem[]): ReagraphNode[] {
  return items.map((item) => ({
    id: nodeId("topic", item.node_id),
    label: truncateLabel(item.title || item.node_id, 48),
    size: NODE_SIZE.topic,
    fill: NODE_COLOR.topic,
    data: { nodeType: "topic", entityId: item.node_id },
  }));
}

function GraphCanvasBackground({ isDark }: { isDark: boolean }) {
  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      aria-hidden
    >
      <div
        className={`absolute inset-0 ${
          isDark
            ? "bg-[radial-gradient(circle_at_center,#1e293b_0%,#0f172a_55%,#020617_100%)]"
            : "bg-[radial-gradient(circle_at_center,#ffffff_0%,#eef2f7_50%,#e2e8f0_100%)]"
        }`}
      />
      {[140, 220, 300, 380, 460].map((radius) => (
        <div
          key={radius}
          className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed ${
            isDark ? "border-slate-600/30" : "border-slate-300/45"
          }`}
          style={{ width: radius * 2, height: radius * 2 }}
        />
      ))}
      {PARTICLE_POSITIONS.map(([left, top], index) => (
        <div
          key={index}
          className={`absolute h-1 w-1 rounded-full ${
            isDark ? "bg-slate-500/40" : "bg-slate-400/35"
          }`}
          style={{ left: `${left}%`, top: `${top}%` }}
        />
      ))}
    </div>
  );
}

function GraphControlButton({
  title,
  onClick,
  children,
  active,
}: {
  title: string;
  onClick: () => void;
  children: ReactNode;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      className={`flex h-9 w-9 items-center justify-center rounded-xl border shadow-sm transition ${
        active
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-white/80 bg-white/90 text-slate-600 hover:bg-white hover:text-slate-900"
      }`}
    >
      {children}
    </button>
  );
}

function LegendCard({ isDark }: { isDark: boolean }) {
  const items = [
    { label: "Topic", color: NODE_COLOR.topic },
    { label: "Subject", color: NODE_COLOR.subject },
    { label: "Article", color: NODE_COLOR.article },
    { label: "Selected", color: SELECTED_TOPIC_COLOR, ring: true },
  ];

  return (
    <div
      className={`pointer-events-none absolute bottom-4 left-4 z-10 rounded-2xl border px-4 py-3 shadow-lg backdrop-blur-sm ${
        isDark
          ? "border-slate-700/80 bg-slate-900/85"
          : "border-white/80 bg-white/90"
      }`}
    >
      <p
        className={`mb-2.5 text-[10px] font-bold uppercase tracking-widest ${
          isDark ? "text-slate-400" : "text-slate-500"
        }`}
      >
        Chú thích
      </p>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2.5">
            <span
              className={`h-3 w-3 shrink-0 rounded-full ${item.ring ? "ring-2 ring-offset-1" : ""}`}
              style={{
                backgroundColor: item.color,
                ...(item.ring
                  ? {
                      boxShadow: `0 0 0 2px ${item.color}55`,
                      ringColor: item.color,
                    }
                  : {}),
              }}
            />
            <span
              className={`text-xs font-medium ${isDark ? "text-slate-300" : "text-slate-600"}`}
            >
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MinimapPreview({
  imageUrl,
  isDark,
}: {
  imageUrl: string | null;
  isDark: boolean;
}) {
  return (
    <div
      className={`pointer-events-none absolute bottom-4 left-44 z-10 hidden h-[88px] w-[120px] overflow-hidden rounded-xl border shadow-md backdrop-blur-sm sm:block ${
        isDark
          ? "border-slate-700/80 bg-slate-900/80"
          : "border-white/80 bg-white/85"
      }`}
    >
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imageUrl}
          alt="Minimap"
          className="h-full w-full object-cover opacity-90"
        />
      ) : (
        <div className="flex h-full items-center justify-center">
          <div className="flex flex-wrap gap-1 p-2">
            {[
              NODE_COLOR.topic,
              NODE_COLOR.subject,
              NODE_COLOR.article,
              NODE_COLOR.topic,
            ].map((color, i) => (
              <span
                key={i}
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </div>
      )}
      <div className="absolute inset-3 rounded border border-emerald-400/50" />
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: ReactNode;
  tone: "emerald" | "sky" | "violet";
}) {
  const tones = {
    emerald: "bg-emerald-50 text-emerald-900 border-emerald-100",
    sky: "bg-sky-50 text-sky-900 border-sky-100",
    violet: "bg-violet-50 text-violet-900 border-violet-100",
  };

  return (
    <div className={`rounded-xl border px-3 py-2.5 ${tones[tone]}`}>
      <p className="text-[10px] font-semibold uppercase tracking-wide opacity-70">
        {label}
      </p>
      <p className="mt-0.5 text-lg font-bold tabular-nums">{value ?? "—"}</p>
    </div>
  );
}

function DetailRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Hash;
  label: string;
  value: ReactNode;
}) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex gap-3 border-b border-slate-100 py-3 last:border-0">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <dt className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
          {label}
        </dt>
        <dd className="mt-0.5 break-words text-sm leading-relaxed text-slate-800">
          {value}
        </dd>
      </div>
    </div>
  );
}

function NodeTypeBadge({ type }: { type: NodeType }) {
  const styles = {
    topic: "bg-emerald-100 text-emerald-800",
    subject: "bg-sky-100 text-sky-800",
    article: "bg-violet-100 text-violet-800",
  };
  const labels = { topic: "Topic", subject: "Subject", article: "Article" };

  return (
    <span
      className={`inline-flex items-center rounded-lg px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${styles[type]}`}
    >
      {labels[type]}
    </span>
  );
}

export function LegalCorpusVisualize() {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<GraphCanvasRef | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const [graph, setGraph] = useState<GraphState>({ nodes: [], edges: [] });
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [expanding, setExpanding] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [is3D, setIs3D] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [minimapUrl, setMinimapUrl] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const expandedTopics = useRef(new Set<string>());
  const expandedSubjects = useRef(new Set<string>());

  const graphTheme = useMemo(() => buildGraphTheme(isDark), [isDark]);

  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === containerRef.current);
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (graph.nodes.length === 0) return;
    const timer = window.setTimeout(() => {
      try {
        const url = graphRef.current?.exportCanvas();
        if (url) setMinimapUrl(url);
      } catch {
        // exportCanvas may fail before canvas is ready
      }
    }, 800);
    return () => window.clearTimeout(timer);
  }, [graph, selected, is3D, isDark]);

  const toggleFullscreen = useCallback(async () => {
    const el = containerRef.current;
    if (!el) return;
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await el.requestFullscreen();
      }
    } catch {
      // Ignore if blocked
    }
  }, []);

  const handleCenterGraph = useCallback(() => {
    graphRef.current?.fitNodesInView(undefined, { animated: true });
  }, []);

  const handleZoomIn = useCallback(() => {
    graphRef.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    graphRef.current?.zoomOut();
  }, []);

  const { data: topicsEnvelope, isPending: topicsLoading } =
    useAdminLegalTopicsList({ page: 1, page_size: TOPIC_PAGE_SIZE });

  const topicsReady = useMemo(
    () =>
      topicsEnvelope?.code === 200 ? (topicsEnvelope.data?.items ?? []) : [],
    [topicsEnvelope],
  );

  useEffect(() => {
    if (topicsReady.length === 0) return;
    setGraph((prev) => {
      if (prev.nodes.length > 0) return prev;
      return { nodes: topicNodesFromItems(topicsReady), edges: [] };
    });
  }, [topicsReady]);

  const expandTopic = useCallback(async (topicId: string) => {
    expandedTopics.current.add(topicId);
    setExpanding(`topic:${topicId}`);

    try {
      const axiosResponse = await documentService.listAdminLegalSubjects(
        { params: { topic_id: topicId, page: 1, page_size: CHILD_PAGE_SIZE } },
        true,
      );
      const envelope = axiosResponse.data as ApiEnvelope<{
        items: LegalTreeNodeItem[];
      }>;
      const items = envelope?.code === 200 ? (envelope.data?.items ?? []) : [];
      const parentId = nodeId("topic", topicId);

      const newNodes: ReagraphNode[] = items.map((item) => ({
        id: nodeId("subject", item.node_id),
        label: truncateLabel(item.title || item.node_id, 48),
        size: NODE_SIZE.subject,
        fill: NODE_COLOR.subject,
        data: { nodeType: "subject", entityId: item.node_id },
      }));
      const newEdges: GraphEdge[] = newNodes.map((n) => ({
        id: `${parentId}->${n.id}`,
        source: parentId,
        target: n.id,
      }));

      setGraph((prev) => mergeGraph(prev, newNodes, newEdges));
    } finally {
      setExpanding(null);
    }
  }, []);

  const collapseTopic = useCallback((topicId: string) => {
    if (!expandedTopics.current.has(topicId)) return;
    expandedTopics.current.delete(topicId);

    setGraph((prev) => {
      const topicNodeId = nodeId("topic", topicId);
      prev.edges
        .filter((edge) => edge.source === topicNodeId)
        .forEach((edge) => {
          expandedSubjects.current.delete(entityIdFromNodeId(edge.target));
        });
      return collapseBranch(prev, topicNodeId);
    });
  }, []);

  const expandSubject = useCallback(async (subjectId: string) => {
    expandedSubjects.current.add(subjectId);
    setExpanding(`subject:${subjectId}`);

    try {
      const axiosResponse = await documentService.listAdminLegalArticles(
        {
          params: {
            subject_id: subjectId,
            page: 1,
            page_size: CHILD_PAGE_SIZE,
          },
        },
        true,
      );
      const envelope = axiosResponse.data as ApiEnvelope<{
        items: AdminLegalArticleItem[];
      }>;
      const items = envelope?.code === 200 ? (envelope.data?.items ?? []) : [];
      const parentId = nodeId("subject", subjectId);

      const newNodes: ReagraphNode[] = items.map((item) => ({
        id: nodeId("article", String(item.id)),
        label: truncateLabel(
          item.article_title || item.article_anchor || `Article ${item.id}`,
          48,
        ),
        size: NODE_SIZE.article,
        fill: NODE_COLOR.article,
        data: {
          nodeType: "article",
          entityId: String(item.id),
          article: item,
        },
      }));
      const newEdges: GraphEdge[] = newNodes.map((n) => ({
        id: `${parentId}->${n.id}`,
        source: parentId,
        target: n.id,
      }));

      setGraph((prev) => mergeGraph(prev, newNodes, newEdges));
    } finally {
      setExpanding(null);
    }
  }, []);

  const collapseSubject = useCallback((subjectId: string) => {
    if (!expandedSubjects.current.has(subjectId)) return;
    expandedSubjects.current.delete(subjectId);
    setGraph((prev) => collapseBranch(prev, nodeId("subject", subjectId)));
  }, []);

  const handleNodeClick = useCallback(
    (node: InternalGraphNode) => {
      const data = node.data as CorpusNodeData | undefined;
      if (!data?.nodeType || !data.entityId) return;

      setSelected({
        nodeType: data.nodeType,
        entityId: data.entityId,
        label: node.label ?? data.entityId,
        article: data.article,
      });
      setSidebarOpen(true);

      if (data.nodeType === "topic") {
        if (expandedTopics.current.has(data.entityId)) {
          collapseTopic(data.entityId);
        } else {
          void expandTopic(data.entityId);
        }
      } else if (data.nodeType === "subject") {
        if (expandedSubjects.current.has(data.entityId)) {
          collapseSubject(data.entityId);
        } else {
          void expandSubject(data.entityId);
        }
      }
    },
    [collapseSubject, collapseTopic, expandSubject, expandTopic],
  );

  const selectedId = selected
    ? nodeId(selected.nodeType, selected.entityId)
    : undefined;
  const trimmedSearch = searchQuery.trim();

  const searchMatches = useMemo(
    () => findSearchMatches(graph.nodes, searchQuery),
    [graph.nodes, searchQuery],
  );

  const focusSearchMatch = useCallback((match: SearchMatch) => {
    setSelected({
      nodeType: match.nodeType,
      entityId: match.entityId,
      label: match.label,
      article: match.article,
    });
    setSidebarOpen(true);
    setSearchOpen(false);
    window.setTimeout(() => {
      graphRef.current?.centerGraph([match.id], { animated: true });
    }, 50);
  }, []);

  const isSelectedTopicExpanded = useMemo(() => {
    if (selected?.nodeType !== "topic") return false;
    const topicNodeId = nodeId("topic", selected.entityId);
    return graph.edges.some((edge) => edge.source === topicNodeId);
  }, [graph.edges, selected]);

  const isSelectedSubjectExpanded = useMemo(() => {
    if (selected?.nodeType !== "subject") return false;
    const subjectNodeId = nodeId("subject", selected.entityId);
    return graph.edges.some(
      (edge) =>
        edge.source === subjectNodeId && edge.target.startsWith("article:"),
    );
  }, [graph.edges, selected]);

  const canvasGraph = useMemo(() => {
    let next = enrichGraphLabels(graph);
    if (
      selected?.nodeType === "topic" &&
      !trimmedSearch &&
      isSelectedTopicExpanded
    ) {
      next = applyTopicFocusStyle(next, selected.entityId);
    }
    if (
      selected?.nodeType === "subject" &&
      !trimmedSearch &&
      isSelectedSubjectExpanded
    ) {
      next = applySubjectFocusStyle(next, selected.entityId);
    }
    if (trimmedSearch) {
      next = applySearchHighlight(next, searchQuery);
    }
    return next;
  }, [
    graph,
    isSelectedSubjectExpanded,
    isSelectedTopicExpanded,
    searchQuery,
    selected,
    trimmedSearch,
  ]);

  const graphSelections = useMemo(() => {
    if (!selectedId || selected?.nodeType !== "article") return [];
    return [selectedId];
  }, [selected?.nodeType, selectedId]);

  const graphLoading = topicsLoading && graph.nodes.length === 0;
  const topicsError =
    topicsEnvelope && topicsEnvelope.code !== 200 ? topicsEnvelope.msg : null;

  const shellClass = isDark
    ? "border-slate-700/80 bg-slate-900/95 text-slate-100"
    : "border-slate-200/80 bg-white/95 text-slate-900";

  return (
    <div
      ref={containerRef}
      className={`overflow-hidden shadow-xl ring-1 backdrop-blur-sm ${
        isFullscreen
          ? "flex h-screen w-screen flex-col rounded-none ring-slate-700/50"
          : "rounded-3xl ring-slate-200/60"
      } ${shellClass}`}
    >
      <header
        className={`flex flex-col gap-3 border-b px-4 py-4 sm:px-5 lg:flex-row lg:items-center lg:justify-between ${
          isDark
            ? "border-slate-700/80 bg-slate-900/90"
            : "border-slate-100 bg-white/80"
        }`}
      >
        <div className="shrink-0">
          <h2 className="text-lg font-bold tracking-tight sm:text-xl">
            Khám phá Pháp điển
          </h2>
          <p
            className={`text-xs sm:text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}
          >
            Trực quan hóa văn bản luật
          </p>
        </div>

        <div className="relative mx-auto w-full max-w-md flex-1 lg:mx-0">
          <Search
            className={`pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 ${
              isDark ? "text-slate-500" : "text-slate-400"
            }`}
          />
          <input
            ref={searchRef}
            type="search"
            value={searchQuery}
            onChange={(event) => {
              setSearchQuery(event.target.value);
              setSearchOpen(true);
            }}
            onFocus={() => setSearchOpen(true)}
            onBlur={() => {
              window.setTimeout(() => setSearchOpen(false), 150);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && searchMatches[0]) {
                focusSearchMatch(searchMatches[0]);
              }
              if (event.key === "Escape") {
                setSearchQuery("");
                setSearchOpen(false);
              }
            }}
            placeholder="Tìm theo title đang hiển thị…"
            className={`w-full rounded-xl border py-2.5 pl-10 text-sm outline-none transition focus:ring-2 focus:ring-emerald-500/30 ${
              trimmedSearch ? "pr-24" : "pr-16"
            } ${
              isDark
                ? "border-slate-700 bg-slate-800 text-slate-100 placeholder:text-slate-500"
                : "border-slate-200 bg-slate-50 text-slate-900 placeholder:text-slate-400"
            }`}
          />
          {trimmedSearch ? (
            <span
              className={`pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${
                searchMatches.length > 0
                  ? isDark
                    ? "bg-amber-500/20 text-amber-300"
                    : "bg-amber-100 text-amber-800"
                  : isDark
                    ? "bg-slate-700 text-slate-400"
                    : "bg-slate-200 text-slate-500"
              }`}
            >
              {searchMatches.length} kết quả
            </span>
          ) : (
            <kbd
              className={`pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border px-1.5 py-0.5 text-[10px] font-medium sm:inline ${
                isDark
                  ? "border-slate-600 bg-slate-800 text-slate-400"
                  : "border-slate-200 bg-white text-slate-400"
              }`}
            >
              ⌘K
            </kbd>
          )}

          {searchOpen && trimmedSearch && (
            <div
              className={`absolute left-0 right-0 top-[calc(100%+6px)] z-30 max-h-64 overflow-y-auto rounded-xl border shadow-xl ${
                isDark
                  ? "border-slate-700 bg-slate-900"
                  : "border-slate-200 bg-white"
              }`}
            >
              {searchMatches.length === 0 ? (
                <p
                  className={`px-4 py-3 text-sm ${
                    isDark ? "text-slate-400" : "text-slate-500"
                  }`}
                >
                  Không tìm thấy title nào khớp trên đồ thị.
                </p>
              ) : (
                searchMatches.map((match) => (
                  <button
                    key={match.id}
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => focusSearchMatch(match)}
                    className={`flex w-full items-start gap-3 border-b px-4 py-2.5 text-left transition last:border-0 ${
                      isDark
                        ? "border-slate-800 hover:bg-slate-800"
                        : "border-slate-100 hover:bg-slate-50"
                    }`}
                  >
                    <span
                      className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{
                        backgroundColor:
                          match.kind === "prefix"
                            ? SEARCH_COLOR_PREFIX
                            : SEARCH_COLOR_CONTAINS,
                      }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-inherit">
                        {match.label}
                      </span>
                      <span
                        className={`mt-0.5 block text-[10px] font-semibold uppercase tracking-wide ${
                          isDark ? "text-slate-500" : "text-slate-400"
                        }`}
                      >
                        {match.nodeType}
                        {match.kind === "prefix"
                          ? " • bắt đầu bằng"
                          : " • chứa từ khóa"}
                      </span>
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-center justify-end gap-2">
          <GraphControlButton
            title={is3D ? "Chế độ 2D" : "Chế độ 3D"}
            onClick={() => setIs3D((prev) => !prev)}
            active={is3D}
          >
            <Box className="h-4 w-4" />
          </GraphControlButton>
          <GraphControlButton
            title={isFullscreen ? "Thoát toàn màn hình" : "Toàn màn hình"}
            onClick={() => void toggleFullscreen()}
          >
            {isFullscreen ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </GraphControlButton>
          <GraphControlButton
            title={isDark ? "Giao diện sáng" : "Giao diện tối"}
            onClick={() => setIsDark((prev) => !prev)}
          >
            <Sun className="h-4 w-4" />
          </GraphControlButton>
        </div>
      </header>

      <div
        className={`flex flex-col lg:flex-row ${
          isFullscreen ? "min-h-0 flex-1" : "min-h-[680px]"
        }`}
      >
        <div
          className={`relative min-h-0 flex-1 ${isFullscreen ? "" : "min-h-[520px]"}`}
        >
          <GraphCanvasBackground isDark={isDark} />

          {graphLoading ? (
            <div className="relative z-[1] flex h-full min-h-[520px] items-center justify-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
              <span className={isDark ? "text-slate-300" : "text-slate-600"}>
                Đang tải chủ đề…
              </span>
            </div>
          ) : topicsError ? (
            <div className="relative z-[1] flex h-full min-h-[520px] items-center justify-center px-6 text-center text-sm text-rose-500">
              {topicsError}
            </div>
          ) : graph.nodes.length === 0 ? (
            <div
              className={`relative z-[1] flex h-full min-h-[520px] items-center justify-center text-sm ${
                isDark ? "text-slate-400" : "text-slate-500"
              }`}
            >
              Chưa có dữ liệu để visualize.
            </div>
          ) : (
            <div
              className={`relative z-[1] w-full ${
                isFullscreen ? "h-full min-h-0" : "h-[680px] min-h-[520px]"
              }`}
            >
              <GraphCanvas
                ref={graphRef}
                theme={graphTheme}
                layoutType={is3D ? "forceDirected3d" : "forceDirected2d"}
                edgeInterpolation="curved"
                labelType="nodes"
                animated
                draggable
                nodes={canvasGraph.nodes}
                edges={canvasGraph.edges}
                selections={graphSelections}
                sizingType="none"
                minDistance={GRAPH_MIN_DISTANCE}
                maxDistance={GRAPH_MAX_DISTANCE}
                onNodeClick={handleNodeClick}
              />
            </div>
          )}

          <div className="absolute left-4 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-2">
            <GraphControlButton
              title="Về tổng quan"
              onClick={handleCenterGraph}
            >
              <Home className="h-4 w-4" />
            </GraphControlButton>
            <GraphControlButton
              title="Căn giữa đồ thị"
              onClick={handleCenterGraph}
            >
              <Target className="h-4 w-4" />
            </GraphControlButton>
            <GraphControlButton title="Phóng to" onClick={handleZoomIn}>
              <Plus className="h-4 w-4" />
            </GraphControlButton>
            <GraphControlButton title="Thu nhỏ" onClick={handleZoomOut}>
              <Minus className="h-4 w-4" />
            </GraphControlButton>
          </div>

          <div className="pointer-events-none absolute left-4 top-4 z-10 flex flex-wrap gap-2">
            {(
              [
                ["Topic", NODE_COLOR.topic],
                ["Subject", NODE_COLOR.subject],
                ["Article", NODE_COLOR.article],
              ] as const
            ).map(([label, color]) => (
              <span
                key={label}
                className="rounded-full border border-white/60 bg-white/90 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide shadow-sm backdrop-blur-sm"
                style={{ color }}
              >
                {label}
              </span>
            ))}
          </div>

          <LegendCard isDark={isDark} />
          <MinimapPreview imageUrl={minimapUrl} isDark={isDark} />

          {expanding && (
            <div
              className={`absolute bottom-4 right-4 z-10 flex items-center gap-2 rounded-xl border px-3 py-2 text-xs shadow-lg backdrop-blur-sm ${
                isDark
                  ? "border-slate-700 bg-slate-900/90 text-slate-300"
                  : "border-white bg-white/95 text-slate-600"
              }`}
            >
              <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-500" />
              Đang mở rộng node…
            </div>
          )}
        </div>

        {sidebarOpen && (
          <aside
            className={`flex w-full flex-col border-t lg:w-[400px] lg:shrink-0 lg:border-l lg:border-t-0 ${
              isFullscreen ? "max-h-[42vh] lg:max-h-none" : ""
            } ${isDark ? "border-slate-700/80 bg-slate-900" : "border-slate-100 bg-white"}`}
          >
            <div
              className={`flex items-start justify-between border-b px-5 py-4 ${
                isDark ? "border-slate-700/80" : "border-slate-100"
              }`}
            >
              <div>
                <h3 className="text-base font-bold">Chi tiết node</h3>
                <p
                  className={`mt-0.5 text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}
                >
                  Nhấn Topic/Subject để mở rộng hoặc thu gọn.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSidebarOpen(false)}
                className={`rounded-lg p-1.5 transition ${
                  isDark
                    ? "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                    : "text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                }`}
                aria-label="Đóng panel"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4">
              {!selected ? (
                <div className="flex h-full min-h-[200px] flex-col items-center justify-center text-center">
                  <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                    <Layers className="h-7 w-7" />
                  </div>
                  <p
                    className={`text-sm font-medium ${isDark ? "text-slate-300" : "text-slate-600"}`}
                  >
                    Chọn một node trên đồ thị
                  </p>
                  <p
                    className={`mt-1 text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}
                  >
                    để xem thông tin chi tiết
                  </p>
                </div>
              ) : selected.nodeType === "topic" ? (
                <TopicDetailPanel
                  topicId={selected.entityId}
                  label={selected.label}
                  isExpanded={isSelectedTopicExpanded}
                  onExpandSubjects={() => {
                    if (!isSelectedTopicExpanded) {
                      void expandTopic(selected.entityId);
                    }
                  }}
                />
              ) : selected.nodeType === "subject" ? (
                <SubjectDetailPanel
                  subjectId={selected.entityId}
                  label={selected.label}
                />
              ) : (
                <ArticleDetailPanel
                  article={selected.article}
                  label={selected.label}
                />
              )}
            </div>
          </aside>
        )}

        {!sidebarOpen && (
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className={`absolute bottom-4 right-4 z-20 rounded-xl border px-4 py-2 text-sm font-semibold shadow-lg lg:static lg:hidden ${
              isDark
                ? "border-slate-700 bg-slate-800 text-slate-200"
                : "border-slate-200 bg-white text-slate-700"
            }`}
          >
            Mở chi tiết
          </button>
        )}
      </div>
    </div>
  );
}

function TopicDetailPanel({
  topicId,
  label,
  isExpanded,
  onExpandSubjects,
}: {
  topicId: string;
  label: string;
  isExpanded: boolean;
  onExpandSubjects: () => void;
}) {
  const { data: envelope, isPending } = useAdminLegalTopicDetail(topicId);
  const detail =
    envelope?.code === 200
      ? (envelope.data as AdminLegalTopicDetail)
      : undefined;

  if (isPending) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Đang tải topic…
      </div>
    );
  }

  if (envelope && envelope.code !== 200) {
    return (
      <p className="text-sm text-rose-600">
        {envelope.msg || "Không tải được topic"}
      </p>
    );
  }

  const depth =
    detail?.demuc_count && detail.demuc_count > 0
      ? 2
      : detail?.article_count && detail.article_count > 0
        ? 1
        : 0;

  const exportData = () => {
    const blob = new Blob([JSON.stringify(detail, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `topic-${topicId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-full flex-col">
      <NodeTypeBadge type="topic" />
      <h4 className="mt-3 text-xl font-bold leading-snug text-slate-900">
        {detail?.topic_title_vi || label}
      </h4>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <StatCard
          label="Số điều"
          value={detail?.article_count?.toLocaleString("vi-VN")}
          tone="emerald"
        />
        <StatCard
          label="Số đề mục"
          value={detail?.demuc_count?.toLocaleString("vi-VN")}
          tone="sky"
        />
        <StatCard label="Độ sâu" value={depth} tone="violet" />
      </div>

      <dl className="mt-4">
        <DetailRow
          icon={FileText}
          label="Tiêu đề (EN)"
          value={detail?.topic_title_en}
        />
        <DetailRow icon={FileText} label="Ghi chú" value={detail?.topic_note} />
      </dl>

      <div className="mt-auto space-y-2 pt-6">
        <button
          type="button"
          onClick={onExpandSubjects}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700"
        >
          {isExpanded ? "Subject đang hiển thị" : "Xem các subject"}
          <ArrowRight className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={exportData}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          <Download className="h-4 w-4" />
          Xuất dữ liệu
        </button>
      </div>
    </div>
  );
}

function SubjectDetailPanel({
  subjectId,
  label,
}: {
  subjectId: string;
  label: string;
}) {
  const { data: envelope, isPending } = useAdminLegalSubjectDetail(subjectId);
  const detail =
    envelope?.code === 200
      ? (envelope.data as AdminLegalSubjectDetail)
      : undefined;

  if (isPending) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Đang tải subject…
      </div>
    );
  }

  if (envelope && envelope.code !== 200) {
    return (
      <p className="text-sm text-rose-600">
        {envelope.msg || "Không tải được subject"}
      </p>
    );
  }

  return (
    <div>
      <NodeTypeBadge type="subject" />
      <h4 className="mt-3 text-xl font-bold leading-snug text-slate-900">
        {detail?.subject_title || label}
      </h4>

      <dl className="mt-4">
        <DetailRow icon={FileText} label="Chủ đề" value={detail?.topic_title} />
        <DetailRow
          icon={ListOrdered}
          label="Số subject"
          value={detail?.subject_number}
        />
        <DetailRow
          icon={FileText}
          label="Source URL"
          value={detail?.source_url}
        />
      </dl>
    </div>
  );
}

function ArticleDetailPanel({
  article,
  label,
}: {
  article?: AdminLegalArticleItem;
  label: string;
}) {
  if (!article) {
    return (
      <div>
        <NodeTypeBadge type="article" />
        <h4 className="mt-3 text-xl font-bold text-slate-900">{label}</h4>
        <p className="mt-3 text-sm text-slate-500">
          Không có dữ liệu chi tiết.
        </p>
      </div>
    );
  }

  return (
    <div>
      <NodeTypeBadge type="article" />
      <h4 className="mt-3 text-xl font-bold leading-snug text-slate-900">
        {article.article_title || label}
      </h4>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <StatCard
          label="Số ký tự"
          value={article.content_char_len?.toLocaleString("vi-VN")}
          tone="sky"
        />
        <StatCard
          label="Số từ"
          value={article.content_word_count?.toLocaleString("vi-VN")}
          tone="violet"
        />
      </div>

      <dl className="mt-4">
        <DetailRow
          icon={Hash}
          label="Article anchor"
          value={article.article_anchor}
        />
        <DetailRow
          icon={FileText}
          label="Chapter"
          value={article.chapter_title}
        />
        <DetailRow
          icon={FileText}
          label="Subject"
          value={article.subject_title}
        />
        <DetailRow icon={FileText} label="Topic" value={article.topic_title} />

        <DetailRow
          icon={FileText}
          label="Nội dung"
          value={
            article.content_text ? (
              <p className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
                {article.content_text}
              </p>
            ) : null
          }
        />
      </dl>
    </div>
  );
}
