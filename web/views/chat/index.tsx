"use client";

import { useState } from "react";
import { MOCK_CONVERSATION } from "./constants/mockConversation";
import { ChatActions } from "./components/header/ChatActions";
import { ChatHero } from "./components/header/ChatHero";
import { ChatDisclaimer } from "./components/input/ChatDisclaimer";
import { ChatInputBox } from "./components/input/ChatInputBox";
import { ChatLayout } from "./components/layout/ChatLayout";
import { ChatMain } from "./components/layout/ChatMain";
import { Conversation } from "./components/messages/Conversation";

export const ChatView = () => {
  const [inputValue, setInputValue] = useState("");

  const handleSend = () => {
    if (!inputValue.trim()) return;
    setInputValue("");
  };

  return (
    <ChatLayout>
      <ChatMain>
        <ChatActions />
        <ChatHero />
        <Conversation messages={MOCK_CONVERSATION} />
      </ChatMain>

      <ChatInputBox
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSend}
      />
      <ChatDisclaimer />
    </ChatLayout>
  );
};
