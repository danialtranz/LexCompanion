import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
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
}

function buildGridClass(historyOpen: boolean, hasRightPanel: boolean): string {
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
}: ChatLayoutProps) => {
  const hasRightPanel = Boolean(panelRight);
  const [rightPanelWidth, setRightPanelWidth] = useState(400);
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    if (!isResizing) return;

    const onMouseMove = (event: MouseEvent) => {
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
  }, [historyOpen, isResizing]);

  const mainStyle = useMemo(
    () =>
      ({
        "--chat-right-width": `${rightPanelWidth}px`,
      }) as CSSProperties,
    [rightPanelWidth],
  );

  return (
    <main
      style={mainStyle}
      className={`grid min-h-screen grid-cols-1 bg-[#faf7f2] ${buildGridClass(
        historyOpen,
        hasRightPanel,
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
            aria-label="Kéo để thay đổi độ rộng panel"
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
