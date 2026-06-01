"use client";

import { useCallback, useMemo, useState } from "react";
import type { ChatReferenceItem } from "./types";

export function useChatReferences() {
  const [topics, setTopics] = useState<ChatReferenceItem[]>([]);
  const [subjects, setSubjects] = useState<ChatReferenceItem[]>([]);

  const addReference = useCallback((item: ChatReferenceItem) => {
    if (item.nodeType === "topic") {
      setTopics((prev) =>
        prev.some((t) => t.id === item.id) ? prev : [...prev, item],
      );
      return;
    }
    setSubjects((prev) =>
      prev.some((s) => s.id === item.id) ? prev : [...prev, item],
    );
  }, []);

  const removeTopic = useCallback((id: string) => {
    setTopics((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const removeSubject = useCallback((id: string) => {
    setSubjects((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setTopics([]);
    setSubjects([]);
  }, []);

  const topicIds = useMemo(() => topics.map((t) => t.id), [topics]);
  const subjectIds = useMemo(() => subjects.map((s) => s.id), [subjects]);
  const hasReferences = topics.length > 0 || subjects.length > 0;

  const hasReference = useCallback(
    (id: string, nodeType: "topic" | "subject") => {
      if (nodeType === "topic") {
        return topics.some((t) => t.id === id);
      }
      return subjects.some((s) => s.id === id);
    },
    [subjects, topics],
  );

  return {
    topics,
    subjects,
    topicIds,
    subjectIds,
    hasReferences,
    hasReference,
    addReference,
    removeTopic,
    removeSubject,
    clearAll,
  };
}

export type ChatReferencesState = ReturnType<typeof useChatReferences>;
