"use client";

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Info, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { UploadUserDocumentData } from "@/hooks/useDocumentHook";
import { PanelRight } from "../panelRight/PanelRight";
import { FileTable } from "./FileTable";
import { UploadBox } from "./UploadBox";

type KnowledgeBasePanelProps = {
  kb_id?: string | null;
  onClose: () => void;
  onUploadSuccess?: (data: UploadUserDocumentData) => void;
};

export const KnowledgeBasePanel = ({
  kb_id = null,
  onClose,
  onUploadSuccess,
}: KnowledgeBasePanelProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const handleUploadSuccess = useCallback(
    (data: UploadUserDocumentData) => {
      onUploadSuccess?.(data);
      void queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
    },
    [onUploadSuccess, queryClient],
  );

  return (
    <PanelRight>
      <div className="flex h-[60px] shrink-0 items-center gap-2 border-b border-[#ebe3d6] px-5">
        <h2 className="m-0 flex-1 text-sm font-bold text-[#2c2620]">
          {t("chat.knowledgeBase.title")}
        </h2>
        <button
          type="button"
          aria-label={t("chat.knowledgeBase.info")}
          className="grid h-8 w-8 place-items-center rounded-lg border-0 bg-transparent text-[#8a8178] transition-colors hover:bg-[#faf5ec] hover:text-[#9a6c2b] cursor-pointer"
        >
          <Info className="h-4 w-4" strokeWidth={2} />
        </button>
        <button
          type="button"
          aria-label={t("chat.knowledgeBase.close")}
          onClick={onClose}
          className="grid h-8 w-8 place-items-center rounded-lg border-0 bg-transparent text-[#8a8178] transition-colors hover:bg-[#faf5ec] hover:text-[#2c2620] cursor-pointer"
        >
          <X className="h-4 w-4" strokeWidth={2} />
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 py-5">
        <UploadBox onUploadSuccess={handleUploadSuccess} />
        <FileTable kb_id={kb_id} />
      </div>
    </PanelRight>
  );
};
