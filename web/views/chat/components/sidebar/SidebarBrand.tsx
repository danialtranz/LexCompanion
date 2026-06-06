import Image from "next/image";

const LAWBOT_LOGO = "/images/icons/lex-companion-logo.png";

export const SidebarBrand = () => (
  <div className="mb-5 flex items-center gap-3 px-1">
    <div className="relative shrink-0">
      <div className="relative grid h-11 w-11 place-items-center overflow-hidden rounded-full bg-gradient-to-br from-[#fffaf2] via-[#faf3e6] to-[#f0e4d0] p-[2px] shadow-[inset_0_0_0_1px_#ebe3d6,0_2px_8px_rgba(184,122,29,0.1)]">
        <div className="grid h-full w-full place-items-center overflow-hidden rounded-full bg-[#faf3e6]">
          <Image
            src={LAWBOT_LOGO}
            alt="Lex Companion"
            width={28}
            height={28}
            className="h-[112%] w-[112%] max-w-none rounded-full object-cover"
          />
        </div>
      </div>
    </div>
    <div className="min-w-0 text-left">
      <h1 className="m-0 font-serif text-[17px] font-bold tracking-wide text-[#9a6c2b]">
        Lex Companion
      </h1>
    </div>
  </div>
);
