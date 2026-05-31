import Image from "next/image";

const LAWBOT_LOGO = "/images/icons/lawbot-logo.png";

export const SidebarBrand = () => (
  <div className="mb-[52px] text-center">
    <div className="mx-auto mb-3.5 flex h-[72px] w-[72px] items-center justify-center rounded-full bg-[radial-gradient(circle,rgba(217,167,71,0.15),transparent_60%),#fffdf9]">
      <Image
        src={LAWBOT_LOGO}
        alt="LawBot"
        width={48}
        height={48}
        className="h-11 w-11 object-contain"
      />
    </div>
    <h1 className="m-0 font-serif text-[22px] tracking-[0.06em] text-[#b87a1d]">
      LAW BOT
    </h1>
    <p className="mt-1.5 text-xs text-[#7d7164]">Trợ lý pháp lý AI</p>
  </div>
);
