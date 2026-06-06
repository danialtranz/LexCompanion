"use client";

import dynamic from "next/dynamic";
import { forwardRef } from "react";
import { useTranslation } from "react-i18next";
import type { GraphCanvasProps, GraphCanvasRef } from "reagraph";

function GraphLoadingPlaceholder() {
  const { t } = useTranslation();
  return (
    <div className="flex h-full min-h-[420px] items-center justify-center text-sm text-slate-500">
      {t("corpus.loadingGraph")}
    </div>
  );
}

const GraphCanvasBase = dynamic(
  () => import("reagraph").then((mod) => mod.GraphCanvas),
  {
    ssr: false,
    loading: () => <GraphLoadingPlaceholder />,
  },
);

const GraphCanvas = forwardRef<GraphCanvasRef, GraphCanvasProps>(
  function GraphCanvas(props, ref) {
    return <GraphCanvasBase {...props} ref={ref} />;
  },
);

export default GraphCanvas;
