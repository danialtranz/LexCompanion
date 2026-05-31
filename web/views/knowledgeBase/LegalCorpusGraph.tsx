"use client";

import dynamic from "next/dynamic";
import { forwardRef } from "react";
import type { GraphCanvasProps, GraphCanvasRef } from "reagraph";

const GraphCanvasBase = dynamic(
  () => import("reagraph").then((mod) => mod.GraphCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[420px] items-center justify-center text-sm text-slate-500">
        Đang tải đồ thị…
      </div>
    ),
  },
);

const GraphCanvas = forwardRef<GraphCanvasRef, GraphCanvasProps>(
  function GraphCanvas(props, ref) {
    return <GraphCanvasBase {...props} ref={ref} />;
  },
);

export default GraphCanvas;
