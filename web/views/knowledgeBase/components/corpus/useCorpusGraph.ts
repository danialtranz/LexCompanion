"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GraphCanvasRef, GraphEdge, InternalGraphNode } from "reagraph";
import documentService from "@/service/documentService";
import {
  useAdminLegalTopicsList,
  type ApiEnvelope,
  type LegalTreeNodeItem,
} from "@/hooks/useDocumentHook";
import {
  CHILD_PAGE_SIZE,
  NODE_COLOR,
  NODE_SIZE,
  TOPIC_PAGE_SIZE,
} from "./constants";
import {
  applySearchHighlight,
  applySubjectFocusStyle,
  applyTopicFocusStyle,
  buildGraphTheme,
  collapseBranch,
  enrichGraphLabels,
  findSearchMatches,
  mergeGraph,
  nodeId,
  topicNodesFromItems,
  truncateLabel,
} from "./graphUtils";
import type {
  CorpusNodeData,
  GraphState,
  ReagraphNode,
  SearchMatch,
  SelectedNode,
} from "./types";

export function useCorpusGraph(options?: {
  onSelect?: (node: SelectedNode | null) => void;
  consumeIgnoredClick?: () => boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<GraphCanvasRef | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const [graph, setGraph] = useState<GraphState>({ nodes: [], edges: [] });
  const [selected, setSelectedInternal] = useState<SelectedNode | null>(null);
  const [expanding, setExpanding] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [is3D, setIs3D] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [minimapUrl, setMinimapUrl] = useState<string | null>(null);

  const expandedTopics = useRef(new Set<string>());

  const setSelected = useCallback(
    (node: SelectedNode | null) => {
      setSelectedInternal(node);
      options?.onSelect?.(node);
    },
    [options],
  );

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

    setGraph((prev) => collapseBranch(prev, nodeId("topic", topicId)));
  }, []);

  const handleNodeClick = useCallback(
    (node: InternalGraphNode) => {
      if (options?.consumeIgnoredClick?.()) return;

      const data = node.data as CorpusNodeData | undefined;
      if (!data?.nodeType || !data.entityId) return;

      setSelected({
        nodeType: data.nodeType,
        entityId: data.entityId,
        label: node.label ?? data.entityId,
        article: data.article,
      });

      if (data.nodeType === "topic") {
        if (expandedTopics.current.has(data.entityId)) {
          collapseTopic(data.entityId);
          setSelected(null);
        } else {
          void expandTopic(data.entityId);
        }
      }
    },
    [collapseTopic, expandTopic, options, setSelected],
  );

  const handleCanvasClick = useCallback(() => {
    if (options?.consumeIgnoredClick?.()) return;
    setSelected(null);
  }, [options, setSelected]);

  const selectedId = selected
    ? nodeId(selected.nodeType, selected.entityId)
    : undefined;
  const trimmedSearch = searchQuery.trim();

  const searchMatches = useMemo(
    () => findSearchMatches(graph.nodes, searchQuery),
    [graph.nodes, searchQuery],
  );

  const focusSearchMatch = useCallback(
    (match: SearchMatch) => {
      setSelected({
        nodeType: match.nodeType,
        entityId: match.entityId,
        label: match.label,
        article: match.article,
      });
      setSearchOpen(false);
      window.setTimeout(() => {
        graphRef.current?.centerGraph([match.id], { animated: true });
      }, 50);
    },
    [setSelected],
  );

  const isSelectedTopicExpanded = useMemo(() => {
    if (selected?.nodeType !== "topic") return false;
    const topicNodeId = nodeId("topic", selected.entityId);
    return graph.edges.some((edge) => edge.source === topicNodeId);
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
    if (selected?.nodeType === "subject" && !trimmedSearch) {
      next = applySubjectFocusStyle(next, selected.entityId);
    }
    if (trimmedSearch) {
      next = applySearchHighlight(next, searchQuery);
    }
    return next;
  }, [
    graph,
    isSelectedTopicExpanded,
    searchQuery,
    selected,
    trimmedSearch,
  ]);

  const graphSelections = useMemo(() => {
    if (!selectedId || selected?.nodeType === "article") return [];
    if (selected?.nodeType === "topic") {
      if (!isSelectedTopicExpanded) return [];
      const topicNodeId = nodeId("topic", selected.entityId);
      const childSubjectIds = graph.edges
        .filter((edge) => edge.source === topicNodeId)
        .map((edge) => edge.target);
      return [topicNodeId, ...childSubjectIds];
    }
    return [selectedId];
  }, [graph.edges, isSelectedTopicExpanded, selected, selectedId]);

  const graphLoading = topicsLoading && graph.nodes.length === 0;
  const topicsError =
    topicsEnvelope && topicsEnvelope.code !== 200 ? topicsEnvelope.msg : null;

  return {
    containerRef,
    graphRef,
    searchRef,
    graph,
    selected,
    setSelected,
    expanding,
    isFullscreen,
    isDark,
    setIsDark,
    is3D,
    setIs3D,
    searchQuery,
    setSearchQuery,
    searchOpen,
    setSearchOpen,
    minimapUrl,
    graphTheme,
    canvasGraph,
    graphSelections,
    graphLoading,
    topicsError,
    searchMatches,
    trimmedSearch,
    focusSearchMatch,
    isSelectedTopicExpanded,
    handleNodeClick,
    handleCanvasClick,
    handleCenterGraph,
    handleZoomIn,
    handleZoomOut,
    toggleFullscreen,
    expandTopic,
  };
}
