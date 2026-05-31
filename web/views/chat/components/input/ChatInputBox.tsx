import { type FormEvent } from "react";
import { Paperclip, SendHorizontal } from "lucide-react";

interface ChatInputBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSend?: () => void;
}

export const ChatInputBox = ({ value, onChange, onSend }: ChatInputBoxProps) => {
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSend?.();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="fixed bottom-[42px] left-5 right-5 z-20 grid h-16 grid-cols-[1fr_38px_46px] items-center gap-3 rounded-[13px] border border-[#eee4d7] bg-white px-3.5 shadow-[0_18px_45px_rgba(84,59,28,0.09)] sm:left-8 sm:right-8 lg:left-[226px] lg:right-16"
    >
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Nhập câu hỏi của bạn về pháp luật..."
        className="min-w-0 border-0 bg-transparent pl-2 text-[#312b25] outline-none placeholder:text-[#9e958b]"
      />
      <button
        type="button"
        aria-label="Đính kèm tệp"
        className="grid place-items-center border-0 bg-transparent text-[#7d766f] transition-colors hover:text-[#9b6416] cursor-pointer"
      >
        <Paperclip className="h-5 w-5" strokeWidth={2} />
      </button>
      <button
        type="submit"
        aria-label="Gửi tin nhắn"
        className="grid h-[46px] w-[46px] place-items-center rounded-[10px] border-0 bg-gradient-to-br from-[#e8bf73] to-[#b77519] text-white transition-transform hover:-translate-y-px cursor-pointer"
      >
        <SendHorizontal className="h-5 w-5" strokeWidth={2.5} />
      </button>
    </form>
  );
};
