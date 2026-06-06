"use client";

import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { ChatSidebar } from "../sidebar/ChatSidebar";

interface ChatLayoutProps {
  children: ReactNode;
  panelRight?: ReactNode;
  historyPanel?: ReactNode;
  historyOpen?: boolean;
  onCreateConversation?: () => void;
  onOpenKnowledgeBase?: () => void;
  onToggleHistory?: () => void;
  knowledgeBaseActive?: boolean;
  historyActive?: boolean;
  /** Cột chat cố định ~380px; panel văn bản chiếm phần còn lại bên phải. */
  liveDocumentLayout?: boolean;
}

function buildGridClass(
  historyOpen: boolean,
  hasRightPanel: boolean,
  liveDocumentLayout: boolean,
): string {
  if (liveDocumentLayout && hasRightPanel) {
    if (historyOpen) {
      return "lg:grid-cols-[240px_320px_var(--chat-live-width)_10px_minmax(0,1fr)]";
    }
    return "lg:grid-cols-[240px_var(--chat-live-width)_10px_minmax(0,1fr)]";
  }
  if (historyOpen && hasRightPanel) {
    return "lg:grid-cols-[240px_320px_minmax(0,1fr)_10px_var(--chat-right-width)]";
  }
  if (historyOpen) {
    return "lg:grid-cols-[240px_320px_minmax(0,1fr)]";
  }
  if (hasRightPanel) {
    return "lg:grid-cols-[240px_minmax(0,1fr)_10px_var(--chat-right-width)]";
  }
  return "lg:grid-cols-[240px_minmax(0,1fr)]";
}

function clampRightPanelWidth(
  width: number,
  historyOpen: boolean,
  viewportWidth: number,
): number {
  const minWidth = 320;
  const leftReserved = historyOpen ? 240 + 320 : 240;
  const maxByMainSpace = viewportWidth - leftReserved - 520;
  const maxWidth = Math.max(minWidth, Math.min(760, maxByMainSpace));
  return Math.min(Math.max(width, minWidth), maxWidth);
}

function clampLiveChatWidth(
  width: number,
  historyOpen: boolean,
  viewportWidth: number,
): number {
  const minWidth = 300;
  const maxWidth = 480;
  const leftReserved = (historyOpen ? 240 + 320 : 240) + 360;
  const maxByViewport = viewportWidth - leftReserved;
  return Math.min(Math.max(width, minWidth), Math.min(maxWidth, maxByViewport));
}

export const ChatLayout = ({
  children,
  panelRight,
  historyPanel,
  historyOpen = false,
  onCreateConversation,
  onOpenKnowledgeBase,
  onToggleHistory,
  knowledgeBaseActive = false,
  historyActive = false,
  liveDocumentLayout = false,
}: ChatLayoutProps) => {
  const { t } = useTranslation();
  const hasRightPanel = Boolean(panelRight);
  const [rightPanelWidth, setRightPanelWidth] = useState(400);
  const [liveChatWidth, setLiveChatWidth] = useState(380);
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    if (!isResizing) return;

    const onMouseMove = (event: MouseEvent) => {
      if (liveDocumentLayout) {
        const sidebar = 240;
        const history = historyOpen ? 320 : 0;
        const next = clampLiveChatWidth(
          event.clientX - sidebar - history,
          historyOpen,
          window.innerWidth,
        );
        setLiveChatWidth(next);
        return;
      }
      const next = clampRightPanelWidth(
        window.innerWidth - event.clientX,
        historyOpen,
        window.innerWidth,
      );
      setRightPanelWidth(next);
    };
    const onMouseUp = () => setIsResizing(false);

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [historyOpen, isResizing, liveDocumentLayout]);

  const mainStyle = useMemo(
    () =>
      ({
        "--chat-right-width": `${rightPanelWidth}px`,
        "--chat-live-width": `${liveChatWidth}px`,
      }) as CSSProperties,
    [rightPanelWidth, liveChatWidth],
  );

  return (
    <main
      style={mainStyle}
      className={`grid min-h-screen grid-cols-1 bg-[#faf7f2] ${buildGridClass(
        historyOpen,
        hasRightPanel,
        liveDocumentLayout,
      )}`}
    >
      <ChatSidebar
        onCreateConversation={onCreateConversation}
        onOpenKnowledgeBase={onOpenKnowledgeBase}
        onToggleHistory={onToggleHistory}
        knowledgeBaseActive={knowledgeBaseActive}
        historyActive={historyActive}
      />
      {historyPanel}
      {children}
      {hasRightPanel && (
        <div
          role="separator"
          aria-orientation="vertical"
          className="relative hidden bg-[#faf7f2] lg:block"
        >
          <button
            type="button"
            aria-label={t("chat.layout.resizePanel")}
            onMouseDown={() => setIsResizing(true)}
            className="absolute inset-y-0 left-1/2 w-2 -translate-x-1/2 cursor-col-resize border-0 bg-transparent p-0"
          >
            <span className="absolute inset-y-4 left-1/2 w-[2px] -translate-x-1/2 rounded-full bg-[#e2d6c6]" />
          </button>
        </div>
      )}
      {panelRight}
    </main>
  );
};
