"use client";

import type { PointerEvent as ReactPointerEvent } from "react";
import {
  Home,
  Loader2,
  Minus,
  Plus,
  Target,
} from "lucide-react";
import type { InternalGraphNode } from "reagraph";
import GraphCanvas from "../../LegalCorpusGraph";
import {
  GRAPH_MAX_DISTANCE,
  GRAPH_MIN_DISTANCE,
  NODE_COLOR,
} from "./constants";
import { GraphCanvasBackground } from "./graph/GraphCanvasBackground";
import { GraphControlButton } from "./graph/GraphControlButton";
import { LegendCard } from "./graph/LegendCard";
import { MinimapPreview } from "./graph/MinimapPreview";
import type { useCorpusGraph } from "./useCorpusGraph";

type CorpusGraph = ReturnType<typeof useCorpusGraph>;

export function LegalCorpusGraphPanel({
  graph,
  isFullscreen,
  onNodePointerOver,
  onNodePointerOut,
  onGraphPointerDownCapture,
}: {
  graph: CorpusGraph;
  isFullscreen: boolean;
  onNodePointerOver?: (node: InternalGraphNode) => void;
  onNodePointerOut?: (node: InternalGraphNode) => void;
  onGraphPointerDownCapture?: (event: ReactPointerEvent) => void;
}) {
  const {
    graphRef,
    expanding,
    isDark,
    is3D,
    minimapUrl,
    graphTheme,
    canvasGraph,
    graphSelections,
    graphLoading,
    topicsError,
    handleNodeClick,
    handleCanvasClick,
    handleCenterGraph,
    handleZoomIn,
    handleZoomOut,
  } = graph;

  return (
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
      ) : canvasGraph.nodes.length === 0 ? (
        <div
          className={`relative z-[1] flex h-full min-h-[520px] items-center justify-center text-sm ${
            isDark ? "text-slate-400" : "text-slate-500"
          }`}
        >
          Chưa có dữ liệu để visualize.
        </div>
      ) : (
        <div
          className={`relative z-[1] w-full touch-none ${
            isFullscreen ? "h-full min-h-0" : "h-[680px] min-h-[520px]"
          }`}
          onPointerDownCapture={onGraphPointerDownCapture}
        >
          <GraphCanvas
            ref={graphRef}
            theme={graphTheme}
            layoutType={is3D ? "forceDirected3d" : "forceDirected2d"}
            edgeInterpolation="curved"
            labelType="nodes"
            animated
            draggable={false}
            nodes={canvasGraph.nodes}
            edges={canvasGraph.edges}
            selections={graphSelections}
            sizingType="none"
            minDistance={GRAPH_MIN_DISTANCE}
            maxDistance={GRAPH_MAX_DISTANCE}
            onNodeClick={handleNodeClick}
            onCanvasClick={handleCanvasClick}
            onNodePointerOver={onNodePointerOver}
            onNodePointerOut={onNodePointerOut}
          />
        </div>
      )}

      <div className="absolute left-4 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-2">
        <GraphControlButton title="Về tổng quan" onClick={handleCenterGraph}>
          <Home className="h-4 w-4" />
        </GraphControlButton>
        <GraphControlButton title="Căn giữa đồ thị" onClick={handleCenterGraph}>
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
  );
}
