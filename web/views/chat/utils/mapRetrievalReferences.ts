import type { RetrievalReferenceItem } from "@/hooks/useChatHook";
import type { ChatCitation } from "../types";

function buildCitationTitle(ref: RetrievalReferenceItem): string {
  return (
    ref.article_title ||
    ref.subject_title ||
    ref.topic_title ||
    ref.ieee?.replace(/^\[\d+\]\s*/, "") ||
    `Nguồn [${ref.index}]`
  );
}

function buildCitationMeta(ref: RetrievalReferenceItem): string | undefined {
  const parts = [ref.chapter_title, ref.subject_title, ref.topic_title].filter(
    Boolean,
  );
  return parts.length > 0 ? parts.join(" · ") : undefined;
}

function buildCitationExcerpt(ref: RetrievalReferenceItem): string {
  if (ref.content_text?.trim()) return ref.content_text.trim();
  const fromIeee = ref.ieee?.replace(/^\[\d+\]\s*/, "").trim();
  return fromIeee || "";
}

export function mapRetrievalReferencesToCitations(
  references: RetrievalReferenceItem[],
): ChatCitation[] {
  return references.map((ref) => ({
    id: ref.chunk_id || `ref-${ref.index}`,
    index: ref.index,
    title: buildCitationTitle(ref),
    excerpt: buildCitationExcerpt(ref),
    href: ref.source_link,
    meta: buildCitationMeta(ref),
  }));
}
