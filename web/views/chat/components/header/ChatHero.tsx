export const ChatHero = () => (
  <div className="flex flex-col items-center justify-center py-16 text-center lg:py-24">
    <div
      aria-hidden
      className="mb-6 grid h-20 w-20 place-items-center rounded-full bg-[#f5ebe0] text-5xl text-[#c9a06a]"
    >
      ⚖
    </div>
    <h2 className="m-0 max-w-md font-serif text-[26px] font-medium leading-snug text-[#2c2620] sm:text-[30px]">
      Xin chào, tôi có thể{" "}
      <span className="font-bold text-[#b8874a]">giúp gì cho bạn?</span>
    </h2>
    <p className="mt-3 max-w-sm text-sm leading-relaxed text-[#8a8178]">
      Tôi là LawBot — trợ lý AI chuyên sâu về pháp luật Việt Nam. Hãy đặt câu
      hỏi pháp lý của bạn bên dưới.
    </p>
  </div>
);
