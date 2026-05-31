export const ChatHero = () => (
  <div className="mt-16 flex items-center justify-between gap-6 lg:mt-[90px]">
    <div>
      <h2 className="m-0 max-w-[470px] font-serif text-[28px] font-medium leading-[1.22] text-[#201914] sm:text-[34px] lg:text-[38px]">
        Xin chào, tôi có thể{" "}
        <span className="font-bold text-[#c18425]">giúp gì cho bạn?</span>
      </h2>
      <p className="mt-[18px] text-sm text-[#62594f]">
        Tôi là LawBot - Trợ lý AI chuyên sâu về pháp luật Việt Nam.
      </p>
    </div>
    <div
      aria-hidden
      className="hidden h-40 w-[210px] shrink-0 place-items-center text-[132px] text-[#d59d3d] drop-shadow-[0_20px_25px_rgba(157,100,22,0.18)] lg:grid"
    >
      ⚖
    </div>
  </div>
);
