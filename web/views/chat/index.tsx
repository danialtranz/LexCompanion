"use client";

import {
  type DragEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ApiEnvelope } from "@/hooks/useDocumentHook";
import type { UserConversationData } from "@/hooks/useUserConversation";
import type { UploadUserDocumentData } from "@/hooks/useDocumentHook";
import { fetchChatSessionDetail } from "@/hooks/useChatHook";
import {
  DOCUMENT_PREVIEW_BLOB_QK,
  fetchDocumentPreviewBlob,
  useDocumentPreviewBlob,
} from "@/hooks/useDocumentPreviewBlob";
import {
  CONTRACT_DRAFT_VERSIONS_QK,
  fetchContractDraftVersions,
  useContractDraftVersions,
} from "@/hooks/useContractDraftVersions";
import { useQueryClient } from "@tanstack/react-query";
import { useUserConversation } from "@/hooks/useUserConversation";
import { downloadContractDraft } from "./utils/downloadContractDraft";
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
import { LiveChatDisclaimer } from "./components/messages/LiveChatDisclaimer";
import { LiveGuidanceHeader } from "./components/messages/LiveGuidanceHeader";
import { DocumentPreviewPanel } from "./components/documentPreview";
import { CitationPanel } from "./components/panelRight/CitationPanel";
import type { DocumentDraftPanelState } from "./utils/documentDraftFromResponse";
import { documentDraftFromResponse } from "./utils/documentDraftFromResponse";
import {
  errorBotMessage,
  parseConversationResult,
} from "./utils/applyConversationResponse";
import {
  buildFieldValuesSummary,
  findActiveFormFillMessageId,
  getFieldsToFill,
} from "./utils/formFillHitl";
import { MOCK_CONVERSATION } from "./constants/mockConversation";
import type { BotMessage, ChatCitation, ChatMessage, UserMessage } from "./types";
import { formatChatTime } from "./utils/formatChatTime";
import { mapSessionMessagesToChatMessages } from "./utils/mapSessionMessages";
import {
  isChatDocumentDragEvent,
  parseChatDocumentDragPayload,
  type ChatAttachedDocument,
} from "./utils/chatDocumentDrag";

type RightPanelMode = "closed" | "citation" | "knowledge" | "document";

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
  const { converse, loading } = useUserConversation();
  const queryClient = useQueryClient();
  const [documentSections, setDocumentSections] = useState<string[]>([]);
  const [documentPanel, setDocumentPanel] = useState<DocumentDraftPanelState>({
    plainText: "",
    streaming: false,
  });
  const [taskExecutionLive, setTaskExecutionLive] = useState(false);
  const [selectedDraftVersion, setSelectedDraftVersion] = useState<
    number | null
  >(null);
  const [downloadingDraftVersion, setDownloadingDraftVersion] = useState<
    number | null
  >(null);
  const [templateDocumentId, setTemplateDocumentId] = useState<string | null>(
    null,
  );

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
    setTaskExecutionLive(false);
    setSelectedDraftVersion(null);
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

  const activeFormFillMessageId = useMemo(
    () => findActiveFormFillMessageId(messages),
    [messages],
  );

  const chatInputBlockedByForm = activeFormFillMessageId != null;

  const hasChatSession = Boolean(chatSessionId?.trim());
  const contractDraftApisEnabled = hasChatSession && taskExecutionLive;

  const previewTemplateDocId =
    templateDocumentId ?? documentPanel.templateDocumentId ?? null;

  const useMinioDraftPreview =
    rightPanel === "document" &&
    (contractDraftApisEnabled || Boolean(previewTemplateDocId));

  // Gọi ngay khi có session + (task_execution hoặc đang xem panel văn bản).
  const shouldFetchDraftVersions =
    hasChatSession && (taskExecutionLive || rightPanel === "document");

  const {
    versions: draftVersions,
    latestVersion: draftLatestVersion,
    loading: draftVersionsLoading,
    refetch: refetchDraftVersions,
  } = useContractDraftVersions({
    sessionId: chatSessionId,
    enabled: shouldFetchDraftVersions,
  });

  const viewDraftVersion =
    selectedDraftVersion ??
    draftLatestVersion ??
    documentPanel.draftVersion ??
    null;

  const {
    blob: draftPreviewBlob,
    loading: draftPreviewBlobLoading,
    refetch: refetchDraftPreviewBinary,
  } = useDocumentPreviewBlob({
    sessionId: chatSessionId,
    viewVersion: viewDraftVersion,
    templateDocumentId: previewTemplateDocId,
    enabled:
      rightPanel === "document" &&
      (Boolean(previewTemplateDocId) ||
        (hasChatSession && contractDraftApisEnabled)),
  });

  const prefetchContractDraftFromSession = useCallback(
    async (
      sessionId: string,
      versionHint?: number,
      templateDocId?: string | null,
    ) => {
      const sid = sessionId.trim();
      if (!sid) return;
      const tpl =
        templateDocId?.trim() ||
        templateDocumentId?.trim() ||
        documentPanel.templateDocumentId?.trim() ||
        null;
      await queryClient.fetchQuery({
        queryKey: CONTRACT_DRAFT_VERSIONS_QK.list(sid),
        queryFn: () => fetchContractDraftVersions(sid),
      });
      await queryClient.fetchQuery({
        queryKey: DOCUMENT_PREVIEW_BLOB_QK.preview(
          sid,
          versionHint ?? undefined,
          tpl ?? undefined,
        ),
        queryFn: () =>
          fetchDocumentPreviewBlob(sid, versionHint ?? null, tpl),
      });
    },
    [queryClient, templateDocumentId, documentPanel.templateDocumentId],
  );

  const handleSelectDraftVersion = useCallback((version: number) => {
    setSelectedDraftVersion(version);
  }, []);

  const handleDownloadDraftVersion = useCallback(
    async (version: number) => {
      if (!chatSessionId) return;
      setDownloadingDraftVersion(version);
      try {
        await downloadContractDraft({ sessionId: chatSessionId, version });
      } catch {
        /* có thể thêm toast sau */
      } finally {
        setDownloadingDraftVersion(null);
      }
    },
    [chatSessionId],
  );

  useEffect(() => {
    if (!shouldFetchDraftVersions || !chatSessionId) return;
    void refetchDraftVersions();
    void prefetchContractDraftFromSession(
      chatSessionId,
      documentPanel.draftVersion,
    );
  }, [
    shouldFetchDraftVersions,
    chatSessionId,
    documentPanel.draftVersion,
    prefetchContractDraftFromSession,
    refetchDraftVersions,
  ]);

  const applyDraftPanel = useCallback(
    (
      draftUpdate: ReturnType<typeof documentDraftFromResponse>,
    ) => {
      if (!draftUpdate.openDocumentPanel) return;
      setDocumentPanel(draftUpdate.panel);
      if (draftUpdate.panel.templateDocumentId) {
        setTemplateDocumentId(draftUpdate.panel.templateDocumentId);
      }
      setRightPanel("document");
      setHistoryOpen(false);
      setDocumentSections(draftUpdate.sections);
    },
    [],
  );

  const exitTaskExecutionLive = useCallback(() => {
    setTaskExecutionLive(false);
  }, []);

  /** Gửi ui_template khi live; tắt live thì không gửi (BE sẽ route intent lại). */
  const withTaskExecutionPayload = useCallback(
    <T extends { ui_template?: string }>(payload: T): T =>
      taskExecutionLive
        ? { ...payload, ui_template: "task_execution" }
        : payload,
    [taskExecutionLive],
  );

  const applyApiResponse = useCallback(
    async (res: ApiEnvelope<UserConversationData>) => {
      if (res.data?.ui_template === "task_execution") {
        setTaskExecutionLive(true);
      }

      const draftUpdate = documentDraftFromResponse(res.data, []);
      applyDraftPanel(draftUpdate);

      const isTaskExecution = res.data?.ui_template === "task_execution";
      if (isTaskExecution && chatSessionId) {
        await refetchDraftVersions();
      }
      if (draftUpdate.openDocumentPanel && isTaskExecution && chatSessionId) {
        const nextVer = draftUpdate.panel.draftVersion;
        if (nextVer != null) {
          setSelectedDraftVersion((prev) =>
            prev == null || prev === documentPanel.draftVersion ? nextVer : prev,
          );
        }
        const tplId =
          String(res.data?.template_document_id || "").trim() ||
          draftUpdate.panel.templateDocumentId ||
          previewTemplateDocId;
        if (tplId) {
          setTemplateDocumentId(tplId);
        }
        await prefetchContractDraftFromSession(
          chatSessionId,
          draftUpdate.panel.draftVersion,
          tplId,
        );
        await refetchDraftPreviewBinary();
      }

      const { bot, error } = parseConversationResult(res);
      if (bot) {
        setMessages((prev) => [...prev, bot]);
      } else if (error) {
        setMessages((prev) => [...prev, error]);
      }
    },
    [
      applyDraftPanel,
      chatSessionId,
      refetchDraftPreviewBinary,
      refetchDraftVersions,
      prefetchContractDraftFromSession,
      documentPanel.draftVersion,
      previewTemplateDocId,
    ],
  );

  const panelRight = useMemo(() => {
    if (rightPanel === "document") {
      return (
        <DocumentPreviewPanel
          plainText={documentPanel.plainText}
          streaming={documentPanel.streaming || loading}
          chunkCurrent={documentPanel.chunkCurrent}
          chunkTotal={documentPanel.chunkTotal}
          statusLabel={documentPanel.statusLabel}
          liveMode={taskExecutionLive}
          useMinioPreview={useMinioDraftPreview}
          previewBlob={draftPreviewBlob}
          previewBlobLoading={draftPreviewBlobLoading}
          versions={draftVersions}
          versionsLoading={draftVersionsLoading}
          selectedVersion={viewDraftVersion}
          latestVersion={draftLatestVersion}
          onSelectVersion={handleSelectDraftVersion}
          onDownloadVersion={handleDownloadDraftVersion}
          downloadingVersion={downloadingDraftVersion}
          onClose={closeRightPanel}
        />
      );
    }
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
    documentPanel,
    loading,
    knowledgeKbId,
    chatSessionId,
    closeRightPanel,
    handleUploadSuccess,
    searchKeyword,
    selectedCitation,
    taskExecutionLive,
    contractDraftApisEnabled,
    useMinioDraftPreview,
    draftPreviewBlob,
    draftPreviewBlobLoading,
    draftVersions,
    draftVersionsLoading,
    viewDraftVersion,
    draftLatestVersion,
    handleSelectDraftVersion,
    handleDownloadDraftVersion,
    downloadingDraftVersion,
  ]);

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    const docIds = attachedDocuments.map((d) => d.id);
    if ((!text && docIds.length === 0) || loading || chatInputBlockedByForm) {
      return;
    }

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

    if (docIds.length > 0) {
      setTemplateDocumentId(docIds[0] ?? null);
      setRightPanel("document");
      setHistoryOpen(false);
      setDocumentPanel({
        plainText: "",
        streaming: true,
        statusLabel: "Agent đang soạn…",
        templateDocumentId: docIds[0],
      });
    }

    try {
      const res = await converse(
        withTaskExecutionPayload({
          query: text || "Tóm tắt và trả lời dựa trên tài liệu đính kèm.",
          session_id: chatSessionId,
          reference: docIds.length > 0 ? { doc_ids: docIds } : undefined,
        }),
      );
      await applyApiResponse(res);
    } catch {
      setMessages((prev) => [
        ...prev,
        errorBotMessage("Đã xảy ra lỗi khi gọi API tra cứu. Vui lòng thử lại."),
      ]);
    }
  }, [
    inputValue,
    attachedDocuments,
    chatSessionId,
    loading,
    chatInputBlockedByForm,
    converse,
    rightPanel,
    applyApiResponse,
    withTaskExecutionPayload,
  ]);

  const handleFormFillSubmit = useCallback(
    async (messageId: string, fieldValues: Record<string, string>) => {
      const target = messages.find(
        (m): m is BotMessage =>
          m.id === messageId && m.type === "bot" && Boolean(m.formFill),
      );
      const formFill = target?.formFill;
      if (!formFill || formFill.submitted || loading) return;

      const fields = getFieldsToFill(formFill);
      const text = buildFieldValuesSummary(fields, fieldValues);

      try {
        const res = await converse(
          withTaskExecutionPayload({
            query: text || "Tiếp tục điền mẫu",
            session_id: chatSessionId,
            thread_id: formFill.threadId,
            resume: {
              action: "edit",
              payload: {
                field_values: fieldValues,
                text,
              },
            },
          }),
        );
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId && m.type === "bot"
              ? {
                  ...m,
                  formFill: { ...m.formFill!, submitted: true },
                }
              : m,
          ),
        );
        await applyApiResponse(res);
      } catch {
        setMessages((prev) => [
          ...prev,
          errorBotMessage(
            "Không gửi được thông tin điền mẫu. Vui lòng thử lại.",
          ),
        ]);
      }
    },
    [messages, loading, chatSessionId, converse, applyApiResponse, withTaskExecutionPayload],
  );

  const handleFormFillReject = useCallback(
    async (messageId: string) => {
      const target = messages.find(
        (m): m is BotMessage =>
          m.id === messageId && m.type === "bot" && Boolean(m.formFill),
      );
      const formFill = target?.formFill;
      if (!formFill || formFill.submitted || loading) return;

      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId && m.type === "bot"
            ? {
                ...m,
                formFill: { ...m.formFill!, submitted: true },
              }
            : m,
        ),
      );

      try {
        const res = await converse(
          withTaskExecutionPayload({
            query: "Hủy điền mẫu",
            session_id: chatSessionId,
            thread_id: formFill.threadId,
            resume: { action: "reject", payload: {} },
          }),
        );
        await applyApiResponse(res);
      } catch {
        setMessages((prev) => [
          ...prev,
          errorBotMessage("Không hủy được phiên điền mẫu."),
        ]);
      }
    },
    [messages, loading, chatSessionId, converse, applyApiResponse, withTaskExecutionPayload],
  );

  const hasMessages = messages.length > 0;
  const liveMode = taskExecutionLive;
  const liveWithDocument = liveMode && rightPanel === "document";

  const chatFooter = (
    <ChatFooter variant={liveMode ? "live" : "default"}>
      {chatInputBlockedByForm && (
        <p className="mb-2 text-center text-xs text-[#9a6c2b]">
          Vui lòng điền form trong tin nhắn LawBot phía trên, rồi bấm{" "}
          <strong>Gửi thông tin</strong>.
        </p>
      )}
      <ChatInputBox
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSend}
        onOpenKnowledgeBase={openKnowledgeBase}
        onUploadSuccess={handleUploadSuccess}
        sessionId={chatSessionId}
        loading={loading}
        disabled={chatInputBlockedByForm}
        attachedDocuments={attachedDocuments}
        onAttachDocument={handleAttachDocument}
        onRemoveAttachedDocument={handleRemoveAttachedDocument}
        variant={liveMode ? "live" : "default"}
        placeholder={
          chatInputBlockedByForm
            ? "Hoàn thành form điền mẫu phía trên để tiếp tục chat…"
            : undefined
        }
      />
      {liveMode ? <LiveChatDisclaimer /> : <ChatDisclaimer />}
    </ChatFooter>
  );

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
      liveDocumentLayout={liveWithDocument}
      onCreateConversation={handleCreateConversation}
      onOpenKnowledgeBase={openKnowledgeBase}
      onToggleHistory={toggleHistory}
      knowledgeBaseActive={rightPanel === "knowledge"}
      historyActive={historyOpen}
    >
      <ChatMain footer={chatFooter}>
        {liveMode ? (
          <div className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden bg-white">
            <LiveGuidanceHeader onClose={exitTaskExecutionLive} />
            <div
              onDragEnter={handleConversationDragEnter}
              onDragOver={handleConversationDragOver}
              onDragLeave={handleConversationDragLeave}
              onDrop={handleConversationDrop}
              className={`relative min-h-0 flex-1 overflow-y-auto px-4 py-4 ${
                isConversationDragOver
                  ? "bg-[#fff8ec] ring-2 ring-inset ring-[#dcc9a8]"
                  : ""
              }`}
            >
              {isConversationDragOver && (
                <div className="pointer-events-none absolute inset-3 grid place-items-center rounded-xl border-2 border-dashed border-[#c9a06a] bg-[#fffdf9]/90">
                  <p className="text-xs font-medium text-[#9a6c2b]">
                    Thả tài liệu vào đây để đính kèm
                  </p>
                </div>
              )}
              {!hasMessages && <ChatHero />}
              <Conversation
                messages={messages}
                loading={loading && !chatInputBlockedByForm}
                selectedCitation={selectedCitation}
                selectedMessageId={selectedMessageId}
                onSelectCitation={handleSelectCitation}
                searchKeyword={searchKeyword}
                activeFormFillMessageId={activeFormFillMessageId}
                onFormFillSubmit={handleFormFillSubmit}
                onFormFillReject={handleFormFillReject}
                variant="live"
              />
            </div>
          </div>
        ) : (
          <>
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
                loading={loading && !chatInputBlockedByForm}
                selectedCitation={selectedCitation}
                selectedMessageId={selectedMessageId}
                onSelectCitation={handleSelectCitation}
                searchKeyword={searchKeyword}
                activeFormFillMessageId={activeFormFillMessageId}
                onFormFillSubmit={handleFormFillSubmit}
                onFormFillReject={handleFormFillReject}
              />
            </div>
          </>
        )}
      </ChatMain>
    </ChatLayout>
  );
};
