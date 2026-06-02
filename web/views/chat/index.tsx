"use client";

import { type DragEvent, useCallback, useMemo, useState } from "react";
import type { UploadUserDocumentData } from "@/hooks/useDocumentHook";
import {
  fetchChatSessionDetail,
  useChatRetrieval,
} from "@/hooks/useChatHook";
import { ChatHistory } from "./components/ChatHistory";
import { ChatHeader } from "./components/header/ChatHeader";
import { ChatHero } from "./components/header/ChatHero";
import { ChatDisclaimer } from "./components/input/ChatDisclaimer";
import { ChatInputBox } from "./components/input/ChatInputBox";
import { ChatFooter } from "./components/layout/ChatFooter";
import { ChatLayout } from "./components/layout/ChatLayout";
import { ChatMain } from "./components/layout/ChatMain";
import { KnowledgeBasePanel } from "./components/knowledgeBase";
import { Conversation } from "./components/messages/Conversation";
import { CitationPanel } from "./components/panelRight/CitationPanel";
import { MOCK_CONVERSATION } from "./constants/mockConversation";
import type { BotMessage, ChatCitation, ChatMessage, UserMessage } from "./types";
import { formatChatTime } from "./utils/formatChatTime";
import { mapRetrievalReferencesToCitations } from "./utils/mapRetrievalReferences";
import { mapSessionMessagesToChatMessages } from "./utils/mapSessionMessages";
import {
  isChatDocumentDragEvent,
  parseChatDocumentDragPayload,
  type ChatAttachedDocument,
} from "./utils/chatDocumentDrag";

type RightPanelMode = "closed" | "citation" | "knowledge";

function createChatSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return `${Date.now()}${Math.random().toString(16).slice(2)}`.slice(0, 32);
}

export const ChatView = () => {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<ChatCitation | null>(
    null,
  );
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(
    null,
  );
  const [rightPanel, setRightPanel] = useState<RightPanelMode>("closed");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [selectedHistorySessionId, setSelectedHistorySessionId] = useState<
    string | null
  >(null);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [knowledgeKbId, setKnowledgeKbId] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [isConversationDragOver, setIsConversationDragOver] = useState(false);
  const [attachedDocuments, setAttachedDocuments] = useState<
    ChatAttachedDocument[]
  >([]);
  const { retrieve, loading } = useChatRetrieval();

  const closeRightPanel = useCallback(() => {
    setRightPanel("closed");
  }, []);

  const toggleHistory = useCallback(() => {
    setHistoryOpen((open) => {
      if (!open) {
        setRightPanel("closed");
        setSelectedCitation(null);
        setSelectedMessageId(null);
      }
      return !open;
    });
  }, []);

  const openKnowledgeBase = useCallback(() => {
    setHistoryOpen(false);
    setRightPanel("knowledge");
    setSelectedCitation(null);
    setSelectedMessageId(null);
  }, []);

  const handleSelectHistorySession = useCallback(async (sessionId: string) => {
    setSelectedHistorySessionId(sessionId);

    if (sessionId.startsWith("mock-")) {
      setMessages(MOCK_CONVERSATION);
      return;
    }

    setChatSessionId(sessionId);

    try {
      const res = await fetchChatSessionDetail(sessionId);
      if (res.code === 200 && res.data?.messages) {
        setMessages(mapSessionMessagesToChatMessages(res.data.messages));
        setChatSessionId(res.data.session.id);
      }
    } catch {
      /* giữ tin nhắn hiện tại nếu tải session thất bại */
    }
  }, []);

  const handleCreateConversation = useCallback(() => {
    setInputValue("");
    setMessages([]);
    setSelectedCitation(null);
    setSelectedMessageId(null);
    setRightPanel("closed");
    setHistoryOpen(false);
    setSelectedHistorySessionId(null);
    setAttachedDocuments([]);
    setKnowledgeKbId(null);
    setSearchOpen(false);
    setSearchKeyword("");
    setChatSessionId(createChatSessionId());
  }, []);

  const handleDeleteHistorySession = useCallback(
    (sessionId: string) => {
      if (selectedHistorySessionId !== sessionId) return;
      setSelectedHistorySessionId(null);
      setMessages([]);
      setSelectedCitation(null);
      setSelectedMessageId(null);
      setChatSessionId(createChatSessionId());
    },
    [selectedHistorySessionId],
  );

  const toggleSearch = useCallback(() => {
    setSearchOpen((open) => {
      if (open) setSearchKeyword("");
      return !open;
    });
  }, []);

  const handleSelectCitation = useCallback(
    (messageId: string, citation: ChatCitation) => {
      setSelectedMessageId(messageId);
      setSelectedCitation(citation);
      setRightPanel("citation");
    },
    [],
  );

  const handleAttachDocument = useCallback((doc: ChatAttachedDocument) => {
    setAttachedDocuments((prev) => {
      if (prev.some((d) => d.id === doc.id)) return prev;
      return [...prev, doc];
    });
  }, []);

  const handleRemoveAttachedDocument = useCallback((docId: string) => {
    setAttachedDocuments((prev) => prev.filter((d) => d.id !== docId));
  }, []);

  const handleConversationDragEnter = useCallback((event: DragEvent) => {
    if (!isChatDocumentDragEvent(event)) return;
    event.preventDefault();
    setIsConversationDragOver(true);
  }, []);

  const handleConversationDragOver = useCallback((event: DragEvent) => {
    if (!isChatDocumentDragEvent(event)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setIsConversationDragOver(true);
  }, []);

  const handleConversationDragLeave = useCallback((event: DragEvent) => {
    if (!isChatDocumentDragEvent(event)) return;
    const next = event.relatedTarget as Node | null;
    if (next && event.currentTarget.contains(next)) return;
    setIsConversationDragOver(false);
  }, []);

  const handleConversationDrop = useCallback(
    (event: DragEvent) => {
      if (!isChatDocumentDragEvent(event)) return;
      event.preventDefault();
      setIsConversationDragOver(false);
      const doc = parseChatDocumentDragPayload(event.dataTransfer);
      if (doc) handleAttachDocument(doc);
    },
    [handleAttachDocument],
  );

  const handleUploadSuccess = useCallback((data: UploadUserDocumentData) => {
    if (data.kb_id) {
      setKnowledgeKbId(data.kb_id);
    }
    if (data.session_id) {
      setChatSessionId(data.session_id);
    }
  }, []);

  const panelRight = useMemo(() => {
    if (rightPanel === "knowledge") {
      return (
        <KnowledgeBasePanel
          kb_id={knowledgeKbId}
          sessionId={chatSessionId}
          onClose={closeRightPanel}
          onUploadSuccess={handleUploadSuccess}
        />
      );
    }
    if (rightPanel === "citation") {
      return (
        <CitationPanel
          citation={selectedCitation}
          searchKeyword={searchKeyword}
          onClose={closeRightPanel}
        />
      );
    }
    return null;
  }, [
    rightPanel,
    knowledgeKbId,
    chatSessionId,
    closeRightPanel,
    handleUploadSuccess,
    searchKeyword,
    selectedCitation,
  ]);

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    const docIds = attachedDocuments.map((d) => d.id);
    if ((!text && docIds.length === 0) || loading) return;

    if (rightPanel === "citation") {
      setRightPanel("closed");
      setSelectedCitation(null);
      setSelectedMessageId(null);
    }

    const userMessage: UserMessage = {
      id: `user-${Date.now()}`,
      type: "user",
      content: text || "(Tài liệu đính kèm)",
      time: formatChatTime(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setAttachedDocuments([]);

    try {
      const res = await retrieve({
        query: text || "Tóm tắt và trả lời dựa trên tài liệu đính kèm.",
        session_id: chatSessionId,
        reference: docIds.length > 0 ? { doc_ids: docIds } : undefined,
      });

      if (res.code === 200 && res.data?.answer) {
        const botMessage: BotMessage = {
          id: `bot-${Date.now()}`,
          type: "bot",
          content: res.data.answer,
          time: formatChatTime(),
          citations: mapRetrievalReferencesToCitations(
            res.data.reference ?? [],
          ),
        };
        setMessages((prev) => [...prev, botMessage]);
        return;
      }

      const errorMessage: BotMessage = {
        id: `bot-error-${Date.now()}`,
        type: "bot",
        content: res.msg || "Không nhận được câu trả lời từ hệ thống.",
        time: formatChatTime(),
        citations: mapRetrievalReferencesToCitations(
          res.data?.reference ?? [],
        ),
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } catch {
      const errorMessage: BotMessage = {
        id: `bot-error-${Date.now()}`,
        type: "bot",
        content: "Đã xảy ra lỗi khi gọi API tra cứu. Vui lòng thử lại.",
        time: formatChatTime(),
        citations: [],
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  }, [
    inputValue,
    attachedDocuments,
    chatSessionId,
    loading,
    retrieve,
    rightPanel,
  ]);

  const hasMessages = messages.length > 0;

  const historyPanel = historyOpen ? (
    <ChatHistory
      selectedSessionId={selectedHistorySessionId}
      onSelectSession={handleSelectHistorySession}
      onDeleteSession={handleDeleteHistorySession}
    />
  ) : null;

  return (
    <ChatLayout
      panelRight={panelRight}
      historyPanel={historyPanel}
      historyOpen={historyOpen}
      onCreateConversation={handleCreateConversation}
      onOpenKnowledgeBase={openKnowledgeBase}
      onToggleHistory={toggleHistory}
      knowledgeBaseActive={rightPanel === "knowledge"}
      historyActive={historyOpen}
    >
      <ChatMain
        footer={
          <ChatFooter>
            <ChatInputBox
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSend}
              onOpenKnowledgeBase={openKnowledgeBase}
              onUploadSuccess={handleUploadSuccess}
              sessionId={chatSessionId}
              loading={loading}
              attachedDocuments={attachedDocuments}
              onAttachDocument={handleAttachDocument}
              onRemoveAttachedDocument={handleRemoveAttachedDocument}
            />
            <ChatDisclaimer />
          </ChatFooter>
        }
      >
        <ChatHeader
          historyOpen={historyOpen}
          onToggleHistory={toggleHistory}
          searchOpen={searchOpen}
          searchValue={searchKeyword}
          onToggleSearch={toggleSearch}
          onSearchChange={setSearchKeyword}
        />

        <div
          onDragEnter={handleConversationDragEnter}
          onDragOver={handleConversationDragOver}
          onDragLeave={handleConversationDragLeave}
          onDrop={handleConversationDrop}
          className={`relative flex-1 overflow-y-auto px-6 py-6 lg:px-8 ${
            isConversationDragOver
              ? "bg-[#fff8ec] ring-2 ring-inset ring-[#dcc9a8]"
              : ""
          }`}
        >
          {isConversationDragOver && (
            <div className="pointer-events-none absolute inset-4 grid place-items-center rounded-2xl border-2 border-dashed border-[#c9a06a] bg-[#fffdf9]/90">
              <p className="text-sm font-medium text-[#9a6c2b]">
                Thả tài liệu vào đây để đính kèm
              </p>
            </div>
          )}
          {!hasMessages && <ChatHero />}
          <Conversation
            messages={messages}
            loading={loading}
            selectedCitation={selectedCitation}
            selectedMessageId={selectedMessageId}
            onSelectCitation={handleSelectCitation}
            searchKeyword={searchKeyword}
          />
        </div>
      </ChatMain>
    </ChatLayout>
  );
};
