import { darkTheme, lightTheme } from "reagraph";
import type { GraphEdge } from "reagraph";
import type { LegalTreeNodeItem } from "@/hooks/useDocumentHook";
import { translate } from "@/locale/translate";
import {
  DIMMED_EDGE_COLOR,
  NODE_COLOR,
  NODE_SIZE,
  SEARCH_COLOR_CONTAINS,
  SEARCH_COLOR_PREFIX,
  FOCUSED_SUBJECT_COLOR,
  FOCUSED_SUBJECT_EDGE_COLOR,
  FOCUSED_TOPIC_COLOR,
  SELECTED_SUBJECT_COLOR,
  SELECTED_TOPIC_COLOR,
} from "./constants";
import type {
  GraphState,
  NodeType,
  ReagraphNode,
  SearchMatch,
  SearchMatchKind,
} from "./types";

export function buildGraphTheme(isDark: boolean) {
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

export function nodeId(type: NodeType, entityId: string) {
  return `${type}:${entityId}`;
}

export function truncateLabel(text: string, maxLen: number): string {
  const t = text.trim();
  if (t.length <= maxLen) return t;
  return `${t.slice(0, maxLen - 1)}…`;
}

export function entityIdFromNodeId(id: string): string {
  return id.split(":").slice(1).join(":");
}

export function mixWithGray(hex: string, amount = 0.5): string {
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

function topicSubLabel(graph: GraphState, topicNodeId: string): string | undefined {
  const subjectIds = graph.edges
    .filter((edge) => edge.source === topicNodeId)
    .map((edge) => edge.target);
  if (subjectIds.length === 0) return undefined;

  return translate("corpus.graph.subjectCount", {
    count: subjectIds.length.toLocaleString("vi-VN"),
  });
}

export function enrichGraphLabels(graph: GraphState): GraphState {
  return {
    ...graph,
    nodes: graph.nodes.map((node) => {
      if (node.data.nodeType !== "topic") return node;
      const subLabel = topicSubLabel(graph, node.id);
      return subLabel ? { ...node, subLabel } : node;
    }),
  };
}

export function collapseBranch(prev: GraphState, parentNodeId: string): GraphState {
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

export function applyTopicFocusStyle(
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
          fill: FOCUSED_TOPIC_COLOR,
          size: NODE_SIZE.topic * 1.35,
        };
      }
      if (childSubjectIds.has(node.id)) {
        return {
          ...node,
          fill: FOCUSED_SUBJECT_COLOR,
          size: NODE_SIZE.subject * 1.4,
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
        ? { ...edge, fill: FOCUSED_SUBJECT_EDGE_COLOR }
        : { ...edge, fill: DIMMED_EDGE_COLOR },
    ),
  };
}

export function applySubjectFocusStyle(
  graph: GraphState,
  subjectEntityId: string,
): GraphState {
  const subjectNodeId = nodeId("subject", subjectEntityId);
  const parentTopicId = graph.edges.find(
    (edge) => edge.target === subjectNodeId,
  )?.source;
  const focusEdgeIds = new Set(
    graph.edges
      .filter(
        (edge) =>
          edge.target === subjectNodeId ||
          (parentTopicId != null && edge.source === parentTopicId),
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
      if (node.id === parentTopicId) {
        return {
          ...node,
          fill: NODE_COLOR.topic,
          size: NODE_SIZE.topic * 1.1,
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

function normalizeSearchText(text: string): string {
  return text.trim().toLowerCase();
}

function matchSearchTitle(label: string, query: string): SearchMatchKind | null {
  const q = normalizeSearchText(query);
  if (!q) return null;

  const title = normalizeSearchText(label);
  if (title.startsWith(q)) return "prefix";
  if (title.includes(q)) return "contains";
  return null;
}

export function findSearchMatches(
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

export function applySearchHighlight(graph: GraphState, query: string): GraphState {
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

export function mergeGraph(
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

export function topicNodesFromItems(items: LegalTreeNodeItem[]): ReagraphNode[] {
  return items.map((item) => ({
    id: nodeId("topic", item.node_id),
    label: truncateLabel(item.title || item.node_id, 48),
    size: NODE_SIZE.topic,
    fill: NODE_COLOR.topic,
    data: { nodeType: "topic", entityId: item.node_id },
  }));
}
