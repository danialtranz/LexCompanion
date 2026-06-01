import Image from "next/image";

const LAWBOT_LOGO = "/images/icons/lawbot-logo.png";

export const SidebarBrand = () => (
  <div className="mb-5 flex items-center gap-3 px-1">
    <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#faf3e6] ring-1 ring-[#ebe3d6]">
      <Image
        src={LAWBOT_LOGO}
        alt="LawBot"
        width={28}
        height={28}
        className="h-7 w-7 object-contain"
      />
    </div>
    <div className="min-w-0 text-left">
      <h1 className="m-0 font-serif text-[17px] font-bold tracking-wide text-[#9a6c2b]">
        LAW BOT
      </h1>
      <p className="m-0 text-[11px] text-[#8a8178]">Trợ lý pháp lý AI</p>
    </div>
  </div>
);
