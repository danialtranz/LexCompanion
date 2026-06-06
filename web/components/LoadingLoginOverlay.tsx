import Image from "next/image";
import { Loader2 } from "lucide-react";
import { IMAGES } from "@/configs/images";

interface LoadingOverlayProps {
  isLoading: boolean;
}

export const LoadingOverlay = ({ isLoading }: LoadingOverlayProps) => {
  if (!isLoading) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center overflow-hidden px-4"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(250,204,21,0.45),transparent_48%),linear-gradient(180deg,#fffbeb_0%,#fde68a_55%,#fbbf24_100%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_14%,transparent_0_18%,rgba(253,224,71,0.12)_19%,transparent_20%),linear-gradient(90deg,rgba(251,191,36,0.2),transparent_18%,transparent_82%,rgba(251,191,36,0.2))]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(253,224,71,0.35),transparent_68%)] blur-2xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-1/2 h-[280px] w-[640px] -translate-x-1/2 translate-y-1/3 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.28),transparent_70%)] blur-3xl"
      />

      <div className="relative z-10 w-full max-w-[360px] rounded-[14px] border border-[#eee4d7] bg-[rgba(255,255,255,0.92)] px-8 py-10 text-center shadow-[0_18px_45px_rgba(84,59,28,0.12)] backdrop-blur-sm">
        <div className="relative mx-auto mb-5 flex h-[88px] w-[88px] items-center justify-center">
          <div
            aria-hidden
            className="absolute inset-0 rounded-full border-2 border-[#eee4d7] border-t-[#b77519] border-r-[#e8bf73] animate-spin"
          />
          <div className="relative grid h-[72px] w-[72px] place-items-center overflow-hidden rounded-full bg-[#fffaf2] ring-1 ring-[#eee4d7]">
            <Image
              src={IMAGES.lexCompanion.logo}
              alt="Lex Companion"
              width={56}
              height={56}
              priority
              className="h-14 w-14 object-contain"
            />
          </div>
        </div>

        <div className="flex items-center justify-center gap-2">
          <Loader2
            className="h-4 w-4 shrink-0 animate-spin text-[#b77519]"
            strokeWidth={2.5}
            aria-hidden
          />
          <p className="m-0 font-serif text-lg tracking-wide text-[#8b5517]">
            Đang xử lý...
          </p>
        </div>
        <p className="mt-2 m-0 text-sm text-[#8a8177]">
          Vui lòng chờ trong giây lát
        </p>
      </div>
    </div>
  );
};
