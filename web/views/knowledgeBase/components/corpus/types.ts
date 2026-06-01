import type { GraphEdge } from "reagraph";
import type { AdminLegalArticleItem } from "@/hooks/useDocumentHook";

export type NodeType = "topic" | "subject" | "article";

export type CorpusNodeData = {
  nodeType: NodeType;
  entityId: string;
  article?: AdminLegalArticleItem;
};

export type ReagraphNode = {
  id: string;
  label: string;
  subLabel?: string;
  size: number;
  fill: string;
  data: CorpusNodeData;
};

export type GraphState = {
  nodes: ReagraphNode[];
  edges: GraphEdge[];
};

export type SelectedNode = {
  nodeType: NodeType;
  entityId: string;
  label: string;
  article?: AdminLegalArticleItem;
};

export type SearchMatchKind = "prefix" | "contains";

export type SearchMatch = {
  id: string;
  label: string;
  kind: SearchMatchKind;
  nodeType: NodeType;
  entityId: string;
  article?: AdminLegalArticleItem;
};
