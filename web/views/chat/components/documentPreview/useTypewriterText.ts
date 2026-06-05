import { useEffect, useRef, useState } from "react";

/**
 * Hiển thị dần `target` (kiểu agent đang gõ).
 * Khi `target` dài thêm (chunk mới), tiếp tục từ ký tự hiện tại.
 */
export function useTypewriterText(
  target: string,
  options?: { enabled?: boolean; msPerChar?: number },
): string {
  const enabled = options?.enabled ?? true;
  const msPerChar = options?.msPerChar ?? 10;
  const [visible, setVisible] = useState("");
  const visibleRef = useRef("");

  useEffect(() => {
    visibleRef.current = visible;
  }, [visible]);

  useEffect(() => {
    if (!enabled) {
      setVisible(target);
      visibleRef.current = target;
      return;
    }

    if (!target) {
      setVisible("");
      visibleRef.current = "";
      return;
    }

    const start = visibleRef.current;
    if (!target.startsWith(start) || start.length > target.length) {
      setVisible("");
      visibleRef.current = "";
      return;
    }

    let index = start.length;
    if (index >= target.length) {
      return;
    }

    const timer = window.setInterval(() => {
      index += 1;
      const next = target.slice(0, index);
      setVisible(next);
      visibleRef.current = next;
      if (index >= target.length) {
        window.clearInterval(timer);
      }
    }, msPerChar);

    return () => window.clearInterval(timer);
  }, [target, enabled, msPerChar]);

  return enabled ? visible : target;
}
