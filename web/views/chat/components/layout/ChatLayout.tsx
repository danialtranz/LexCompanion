import type { ReactNode } from "react";
import { ChatSidebar } from "../sidebar/ChatSidebar";

interface ChatLayoutProps {
  children: ReactNode;
  panelRight?: ReactNode;
  historyPanel?: ReactNode;
  historyOpen?: boolean;
  onOpenKnowledgeBase?: () => void;
  onToggleHistory?: () => void;
  knowledgeBaseActive?: boolean;
  historyActive?: boolean;
}

function buildGridClass(historyOpen: boolean, hasRightPanel: boolean): string {
  if (historyOpen && hasRightPanel) {
    return "lg:grid-cols-[240px_320px_minmax(0,1fr)_400px]";
  }
  if (historyOpen) {
    return "lg:grid-cols-[240px_320px_minmax(0,1fr)]";
  }
  if (hasRightPanel) {
    return "lg:grid-cols-[240px_minmax(0,1fr)_400px]";
  }
  return "lg:grid-cols-[240px_minmax(0,1fr)]";
}

export const ChatLayout = ({
  children,
  panelRight,
  historyPanel,
  historyOpen = false,
  onOpenKnowledgeBase,
  onToggleHistory,
  knowledgeBaseActive = false,
  historyActive = false,
}: ChatLayoutProps) => (
  <main
    className={`grid min-h-screen grid-cols-1 bg-[#faf7f2] ${buildGridClass(
      historyOpen,
      Boolean(panelRight),
    )}`}
  >
    <ChatSidebar
      onOpenKnowledgeBase={onOpenKnowledgeBase}
      onToggleHistory={onToggleHistory}
      knowledgeBaseActive={knowledgeBaseActive}
      historyActive={historyActive}
    />
    {historyPanel}
    {children}
    {panelRight}
  </main>
);
