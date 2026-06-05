export interface ChatCitation {
  id: string;
  index: number;
  title: string;
  excerpt: string;
  href?: string;
  meta?: string;
}

export interface UserMessage {
  id: string;
  type: "user";
  content: string;
  time: string;
}

export type FormFieldDefinition = {
  id: string;
  label: string;
  required?: boolean;
  anchor_text?: string;
  match_strategy?: string;
  value?: string;
};

export type MessageFormFill = {
  threadId: string;
  submitted?: boolean;
  hitl: {
    kind: "form_fields";
    interrupt_id?: string;
    form_schema: FormFieldDefinition[];
    filled_values?: Record<string, string>;
    missing_field_ids: string[];
    clarification_questions: string[];
    actions: string[];
    chunk_index?: number;
    chunk_total?: number;
  };
};

export interface BotMessage {
  id: string;
  type: "bot";
  content: string;
  time: string;
  citations: ChatCitation[];
  error?: boolean;
  /** HITL điền mẫu — hiển thị FormFill dưới bubble bot */
  formFill?: MessageFormFill;
}

export type ChatMessage = UserMessage | BotMessage;
