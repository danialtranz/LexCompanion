"use client";

import { useCallback, useState } from "react";
import { useChatRetrieval } from "@/hooks/useChatHook";
import { ChatHeader } from "./components/header/ChatHeader";
import { ChatHero } from "./components/header/ChatHero";
import { ChatDisclaimer } from "./components/input/ChatDisclaimer";
import { ChatInputBox } from "./components/input/ChatInputBox";
import { ChatFooter } from "./components/layout/ChatFooter";
import { ChatLayout } from "./components/layout/ChatLayout";
import { ChatMain } from "./components/layout/ChatMain";
import { Conversation } from "./components/messages/Conversation";
import { CitationPanel } from "./components/panelRight/CitationPanel";
import type { BotMessage, ChatCitation, ChatMessage, UserMessage } from "./types";
import { formatChatTime } from "./utils/formatChatTime";
import { mapRetrievalReferencesToCitations } from "./utils/mapRetrievalReferences";

export const ChatView = () => {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<ChatCitation | null>(
    null,
  );
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(
    null,
  );
  const { retrieve, loading } = useChatRetrieval();

  const handleSelectCitation = useCallback(
    (messageId: string, citation: ChatCitation) => {
      setSelectedMessageId(messageId);
      setSelectedCitation(citation);
    },
    [],
  );

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || loading) return;

    setSelectedCitation(null);
    setSelectedMessageId(null);

    const userMessage: UserMessage = {
      id: `user-${Date.now()}`,
      type: "user",
      content: text,
      time: formatChatTime(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");

    try {
      const res = await retrieve({ query: text });

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
  }, [inputValue, loading, retrieve]);

  const hasMessages = messages.length > 0;

  return (
    <ChatLayout panelRight={<CitationPanel citation={selectedCitation} />}>
      <ChatMain
        footer={
          <ChatFooter>
            <ChatInputBox
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSend}
              loading={loading}
            />
            <ChatDisclaimer />
          </ChatFooter>
        }
      >
        <ChatHeader />

        <div className="flex-1 overflow-y-auto px-6 py-6 lg:px-8">
          {!hasMessages && <ChatHero />}
          <Conversation
            messages={messages}
            loading={loading}
            selectedCitation={selectedCitation}
            selectedMessageId={selectedMessageId}
            onSelectCitation={handleSelectCitation}
          />
        </div>
      </ChatMain>
    </ChatLayout>
  );
};
