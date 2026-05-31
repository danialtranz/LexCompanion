import { ArrowUpRight } from "lucide-react";
import type { ChatSource } from "../../types";

interface SourceReferencesProps {
  sources: ChatSource[];
}

export const SourceReferences = ({ sources }: SourceReferencesProps) => (
  <div className="mt-[34px] w-full max-w-[720px] overflow-hidden rounded-[14px] border border-[#eee4d7] bg-white/90 shadow-[0_18px_45px_rgba(84,59,28,0.09)]">
    <h4 className="m-0 px-4 pb-3 pt-4 text-[13px] font-medium text-[#8d8378]">
      Nguồn tham khảo:
    </h4>
    {sources.map((source) => (
      <a
        key={source.id}
        href={source.href ?? "#"}
        className="flex h-[50px] items-center justify-between border-t border-[#eee4d7] px-4 text-sm text-[#3a342d] transition-colors hover:bg-[#fffaf2]"
      >
        <span>📄 {source.title}</span>
        <ArrowUpRight className="h-4 w-4 text-[#9e958b]" strokeWidth={2} />
      </a>
    ))}
  </div>
);
