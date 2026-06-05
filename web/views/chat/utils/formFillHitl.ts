import type { UserConversationData } from "@/hooks/useUserConversation";
import type { FormFieldDefinition, MessageFormFill } from "../types";

export function parseFormSchema(raw: unknown): FormFieldDefinition[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
    .map((item) => ({
      id: String(item.id ?? ""),
      label: String(item.label ?? item.id ?? ""),
      required: Boolean(item.required ?? true),
      anchor_text: item.anchor_text != null ? String(item.anchor_text) : undefined,
      match_strategy:
        item.match_strategy != null ? String(item.match_strategy) : undefined,
      value: item.value != null ? String(item.value) : "",
    }))
    .filter((f) => f.id);
}

export function buildMessageFormFill(
  data: UserConversationData | undefined,
): MessageFormFill | undefined {
  if (!data || data.status !== "waiting_human") return undefined;
  const hitl = data.hitl;
  if (!hitl || hitl.kind !== "form_fields") return undefined;
  const threadId = (data.thread_id || "").trim();
  if (!threadId) return undefined;

  const formSchema = parseFormSchema(hitl.form_schema);
  const filledRaw = hitl.filled_values;
  const filled_values: Record<string, string> = {};
  if (filledRaw && typeof filledRaw === "object") {
    for (const [k, v] of Object.entries(filledRaw as Record<string, unknown>)) {
      if (v != null && String(v).trim()) {
        filled_values[k] = String(v).trim();
      }
    }
  }

  const missing_field_ids = Array.isArray(hitl.missing_field_ids)
    ? hitl.missing_field_ids.map(String)
    : [];

  const clarification_questions = Array.isArray(hitl.clarification_questions)
    ? hitl.clarification_questions.map(String)
    : [];

  const actions = Array.isArray(hitl.actions)
    ? hitl.actions.map(String)
    : ["approve", "edit", "reject"];

  return {
    threadId,
    hitl: {
      kind: "form_fields",
      interrupt_id:
        hitl.interrupt_id != null ? String(hitl.interrupt_id) : undefined,
      form_schema: formSchema,
      filled_values,
      missing_field_ids,
      clarification_questions,
      actions,
      chunk_index:
        typeof hitl.chunk_index === "number" ? hitl.chunk_index : undefined,
      chunk_total:
        typeof hitl.chunk_total === "number" ? hitl.chunk_total : undefined,
    },
  };
}

/** Field cần hiển thị cho user điền (ưu tiên missing_field_ids). */
export function getFieldsToFill(formFill: MessageFormFill): FormFieldDefinition[] {
  const { form_schema, missing_field_ids, filled_values = {} } = formFill.hitl;
  const isEmpty = (f: FormFieldDefinition) =>
    !(filled_values[f.id] || f.value || "").trim();

  if (missing_field_ids.length > 0) {
    const idSet = new Set(missing_field_ids);
    return form_schema.filter((f) => idSet.has(f.id));
  }
  // Hiển thị mọi ô còn trống trong chunk (gồm multi-slot trên cùng dòng)
  return form_schema.filter(isEmpty);
}

export function buildFieldValuesSummary(
  fields: FormFieldDefinition[],
  values: Record<string, string>,
): string {
  return fields
    .map((f) => {
      const v = (values[f.id] || "").trim();
      return v ? `${f.label}: ${v}` : "";
    })
    .filter(Boolean)
    .join("; ");
}

export function findActiveFormFillMessageId(messages: { id: string; type: string; formFill?: MessageFormFill }[]): string | null {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.type !== "bot") continue;
    const bot = m as { formFill?: MessageFormFill };
    if (bot.formFill && !bot.formFill.submitted) {
      return m.id;
    }
  }
  return null;
}
