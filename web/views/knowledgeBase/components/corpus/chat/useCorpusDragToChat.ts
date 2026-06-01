"use client";

import { useCallback, useRef, useState } from "react";
import type { InternalGraphNode } from "reagraph";
import type { CorpusNodeData } from "../types";
import type { ChatReferenceItem } from "./types";
import { CHAT_DROP_ZONE_ATTR } from "./types";

const DRAG_THRESHOLD_PX = 10;

function isChatDropTarget(element: Element | null): boolean {
  return Boolean(element?.closest(`[${CHAT_DROP_ZONE_ATTR}]`));
}

function referenceFromNode(node: InternalGraphNode): ChatReferenceItem | null {
  const data = node.data as CorpusNodeData | undefined;
  if (!data?.entityId) return null;
  if (data.nodeType !== "topic" && data.nodeType !== "subject") return null;
  return {
    id: data.entityId,
    nodeType: data.nodeType,
    label: node.label ?? data.entityId,
  };
}

function isDraggableNode(node: InternalGraphNode | null): node is InternalGraphNode {
  if (!node) return false;
  const data = node.data as CorpusNodeData | undefined;
  return data?.nodeType === "topic" || data?.nodeType === "subject";
}

export function useCorpusDragToChat(onDrop: (item: ChatReferenceItem) => void) {
  const [dragging, setDragging] = useState<ChatReferenceItem | null>(null);
  const [cursor, setCursor] = useState({ x: 0, y: 0 });
  const [isOverChat, setIsOverChat] = useState(false);
  const ignoreNextClickRef = useRef(false);
  const hoveredNodeRef = useRef<InternalGraphNode | null>(null);

  const beginDragSession = useCallback(
    (item: ChatReferenceItem, startX: number, startY: number) => {
      let active = false;

      const onPointerMove = (event: PointerEvent) => {
        if (!active) {
          const distance = Math.hypot(
            event.clientX - startX,
            event.clientY - startY,
          );
          if (distance < DRAG_THRESHOLD_PX) return;
          active = true;
          setDragging(item);
        }
        setCursor({ x: event.clientX, y: event.clientY });
        const target = document.elementFromPoint(event.clientX, event.clientY);
        setIsOverChat(isChatDropTarget(target));
      };

      const onPointerUp = (event: PointerEvent) => {
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);

        if (active) {
          ignoreNextClickRef.current = true;
          const target = document.elementFromPoint(
            event.clientX,
            event.clientY,
          );
          if (isChatDropTarget(target)) {
            onDrop(item);
          }
        }

        setDragging(null);
        setIsOverChat(false);
      };

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
    },
    [onDrop],
  );

  const handleNodePointerOver = useCallback((node: InternalGraphNode) => {
    if (isDraggableNode(node)) {
      hoveredNodeRef.current = node;
    }
  }, []);

  const handleNodePointerOut = useCallback((node: InternalGraphNode) => {
    if (hoveredNodeRef.current?.id === node.id) {
      hoveredNodeRef.current = null;
    }
  }, []);

  const handleGraphPointerDownCapture = useCallback(
    (event: React.PointerEvent) => {
      if (event.button !== 0) return;

      const hovered = hoveredNodeRef.current;
      const item = hovered ? referenceFromNode(hovered) : null;
      if (!item) return;

      // Camera is frozen while hovering a node (reagraph). Do not block
      // pointerdown so a short click still triggers onNodeClick.
      beginDragSession(item, event.clientX, event.clientY);
    },
    [beginDragSession],
  );

  const consumeIgnoredClick = useCallback(() => {
    if (!ignoreNextClickRef.current) return false;
    ignoreNextClickRef.current = false;
    return true;
  }, []);

  return {
    dragging,
    cursor,
    isOverChat,
    handleNodePointerOver,
    handleNodePointerOut,
    handleGraphPointerDownCapture,
    consumeIgnoredClick,
  };
}
