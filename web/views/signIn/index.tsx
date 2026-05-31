import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import Image from "next/image";
import { Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import { GoogleSignInButton } from "./GoogleSignInButton";
import { LoadingOverlay } from "./LoadingOverlay";

type AuthTab = "login" | "signup";

const LAWBOT_LOGO = "/images/icons/lawbot-logo.png";

const FieldIcon = ({ children }: { children: ReactNode }) => (
  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#fff5e3] text-[#b77519]">
    {children}
  </span>
);

const AuthTabs = ({
  activeTab,
  onChange,
}: {
  activeTab: AuthTab;
  onChange: (tab: AuthTab) => void;
}) => (
  <div className="mb-5 flex rounded-[10px] border border-[#eee4d7] bg-[#fffaf2] p-1 sm:mb-6">
    {(
      [
        { id: "login" as const, label: "Đăng nhập" },
        { id: "signup" as const, label: "Đăng ký" },
      ] as const
    ).map(({ id, label }) => (
      <button
        key={id}
        type="button"
        onClick={() => onChange(id)}
        className={`flex-1 rounded-[8px] py-2.5 text-sm font-semibold transition-all duration-300 cursor-pointer ${
          activeTab === id
            ? "bg-white text-[#8b5517] shadow-[0_4px_12px_rgba(184,122,29,0.12)]"
            : "border-0 bg-transparent text-[#8a8177] hover:text-[#6f665c]"
        }`}
      >
        {label}
      </button>
    ))}
  </div>
);

const SocialButtons = ({
  isLoading,
  onLoadingChange,
  mode,
}: {
  isLoading: boolean;
  onLoadingChange: (loading: boolean) => void;
  mode: AuthTab;
}) => (
  <>
    <div className="my-5 flex items-center gap-4 text-[13px] text-[#8e8479] sm:my-7">
      <span className="h-px flex-1 bg-[#eee4d7]" />
      {mode === "login" ? "Hoặc đăng nhập với" : "Hoặc đăng ký với"}
      <span className="h-px flex-1 bg-[#eee4d7]" />
    </div>

    <div className="grid grid-cols-1 gap-[14px]">
      <GoogleSignInButton
        disabled={isLoading}
        onLoadingChange={onLoadingChange}
      />
    </div>
  </>
);

const PasswordField = ({
  label,
  value,
  onChange,
  placeholder,
  showPassword,
  onToggle,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  showPassword: boolean;
  onToggle: () => void;
}) => (
  <>
    <label className="mb-2 mt-4 block text-sm font-medium text-[#2f2923] sm:mb-[9px] sm:mt-[22px]">
      {label}
    </label>
    <div className="flex h-[50px] items-center gap-3 rounded-[9px] border border-[#eee4d7] bg-white px-[14px] transition-colors focus-within:border-[#e7bd67] focus-within:ring-2 focus-within:ring-[#e7bd67]/25 sm:h-[54px]">
      <FieldIcon>
        <Lock className="h-4 w-4" strokeWidth={2} />
      </FieldIcon>
      <input
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full border-0 bg-transparent text-[#29231d] outline-none placeholder:text-[#9e958b]"
      />
      <button
        type="button"
        onClick={onToggle}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-0 bg-transparent text-[#9e958b] transition-colors hover:bg-[#fff5e3] hover:text-[#b77519] cursor-pointer"
        aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
      >
        {showPassword ? (
          <EyeOff className="h-4 w-4" strokeWidth={2} />
        ) : (
          <Eye className="h-4 w-4" strokeWidth={2} />
        )}
      </button>
    </div>
  </>
);

const EmailField = ({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) => (
  <>
    <label className="mb-2 mt-4 block text-sm font-medium text-[#2f2923] sm:mb-[9px] sm:mt-[22px]">
      Email
    </label>
    <div className="flex h-[50px] items-center gap-3 rounded-[9px] border border-[#eee4d7] bg-white px-[14px] transition-colors focus-within:border-[#e7bd67] focus-within:ring-2 focus-within:ring-[#e7bd67]/25 sm:h-[54px]">
      <FieldIcon>
        <Mail className="h-4 w-4" strokeWidth={2} />
      </FieldIcon>
      <input
        type="email"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Nhập email của bạn"
        className="w-full border-0 bg-transparent text-[#29231d] outline-none placeholder:text-[#9e958b]"
      />
    </div>
  </>
);

export const SiginInView = () => {
  const [activeTab, setActiveTab] = useState<AuthTab>("login");
  const [isLoading, setIsLoading] = useState(false);
  const [loginHeight, setLoginHeight] = useState(0);
  const [signupHeight, setSignupHeight] = useState(0);

  const loginRef = useRef<HTMLDivElement>(null);
  const signupRef = useRef<HTMLDivElement>(null);

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);

  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupConfirmPassword, setSignupConfirmPassword] = useState("");
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [showSignupConfirmPassword, setShowSignupConfirmPassword] =
    useState(false);

  const handleTabChange = (tab: AuthTab) => {
    if (tab !== activeTab) {
      setActiveTab(tab);
    }
  };

  useLayoutEffect(() => {
    const measure = (element: HTMLDivElement | null, setter: (h: number) => void) => {
      if (!element) return;
      setter(element.getBoundingClientRect().height);
    };

    const updateHeights = () => {
      measure(loginRef.current, setLoginHeight);
      measure(signupRef.current, setSignupHeight);
    };

    updateHeights();

    const observer = new ResizeObserver(updateHeights);
    if (loginRef.current) observer.observe(loginRef.current);
    if (signupRef.current) observer.observe(signupRef.current);

    window.addEventListener("resize", updateHeights);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateHeights);
    };
  }, []);

  const flipHeight = activeTab === "login" ? loginHeight : signupHeight;

  return (
    <main className="relative min-h-screen grid place-items-center overflow-hidden px-4 py-6 text-[#201914] font-sans sm:py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(213,162,66,0.22),transparent_42%),linear-gradient(180deg,#fffdf8_0%,#f3ece2_100%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_14%,transparent_0_18%,rgba(226,182,101,0.05)_19%,transparent_20%),linear-gradient(90deg,rgba(214,162,67,0.12),transparent_18%,transparent_82%,rgba(214,162,67,0.12))]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(217,168,76,0.18),transparent_68%)] blur-2xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-1/2 h-[280px] w-[640px] -translate-x-1/2 translate-y-1/3 rounded-full bg-[radial-gradient(circle,rgba(184,122,29,0.1),transparent_70%)] blur-3xl"
      />

      <div className="relative z-10 w-full max-w-[460px]">
        <div className="rounded-[14px] border border-[#eee4d7] bg-[rgba(255,255,255,0.92)] px-5 py-7 text-center shadow-[0_18px_45px_rgba(84,59,28,0.12)] sm:px-9 sm:py-10">
          <div className="mx-auto mb-4 flex justify-center sm:mb-[18px]">
            <Image
              src={LAWBOT_LOGO}
              alt="LawBot Logo"
              width={120}
              height={120}
              priority
              className="h-[88px] w-[88px] object-contain drop-shadow-[0_8px_18px_rgba(184,122,29,0.18)] sm:h-[120px] sm:w-[120px]"
            />
          </div>

          <h1 className="m-0 font-serif text-4xl tracking-[0.08em] text-[#8b5517] sm:text-[50px]">
            LAWBOT
          </h1>
          <p className="mb-5 mt-2 text-xs tracking-[0.12em] text-[#4c4740] sm:mb-6 sm:mt-[10px] sm:text-base">
            TRỢ LÝ PHÁP LÝ AI
          </p>

          <AuthTabs activeTab={activeTab} onChange={handleTabChange} />

          <div
            className="overflow-hidden transition-[height] duration-[650ms] ease-in-out [perspective:1200px]"
            style={{ height: flipHeight > 0 ? flipHeight : "auto" }}
          >
            <div
              className="relative w-full transition-transform duration-[650ms] ease-in-out will-change-transform [transform-style:preserve-3d]"
              style={{
                height: flipHeight > 0 ? flipHeight : "auto",
                transform:
                  activeTab === "signup" ? "rotateY(180deg)" : "rotateY(0deg)",
              }}
            >
              <div
                ref={loginRef}
                className="w-full text-left [backface-visibility:hidden]"
                style={{
                  transform: "rotateY(0deg)",
                  pointerEvents: activeTab === "login" ? "auto" : "none",
                }}
              >
                <form onSubmit={(event) => event.preventDefault()}>
                  <p className="mb-5 text-center text-sm text-[#6f665c] sm:mb-[30px]">
                    Đăng nhập để tiếp tục sử dụng LawBot
                  </p>

                  <EmailField value={loginEmail} onChange={setLoginEmail} />

                  <PasswordField
                    label="Mật khẩu"
                    value={loginPassword}
                    onChange={setLoginPassword}
                    placeholder="Nhập mật khẩu của bạn"
                    showPassword={showLoginPassword}
                    onToggle={() => setShowLoginPassword((prev) => !prev)}
                  />

                  <button
                    type="button"
                    className="mb-4 mt-3 block w-full border-0 bg-transparent p-0 text-right text-[13px] text-[#9b6416] transition-colors hover:text-[#8b5517] cursor-pointer sm:mb-[22px] sm:mt-[13px]"
                  >
                    Quên mật khẩu?
                  </button>

                  <button
                    type="button"
                    className="h-[52px] w-full rounded-[9px] border-0 text-base font-extrabold text-white bg-gradient-to-br from-[#e8bf73] to-[#b77519] shadow-[0_12px_26px_rgba(184,122,29,0.2)] transition-transform hover:-translate-y-px hover:shadow-[0_14px_30px_rgba(184,122,29,0.28)] cursor-pointer sm:h-14"
                  >
                    Đăng nhập
                  </button>

                  <SocialButtons
                    isLoading={isLoading}
                    onLoadingChange={setIsLoading}
                    mode="login"
                  />

                  <p className="mt-5 text-center text-sm text-[#8a8177] sm:mt-7">
                    Chưa có tài khoản?{" "}
                    <button
                      type="button"
                      onClick={() => handleTabChange("signup")}
                      className="border-0 bg-transparent p-0 font-bold text-[#9b6416] transition-colors hover:text-[#8b5517] cursor-pointer"
                    >
                      Đăng ký ngay
                    </button>
                  </p>
                </form>
              </div>

              <div
                ref={signupRef}
                className="absolute inset-x-0 top-0 w-full text-left [backface-visibility:hidden]"
                style={{
                  transform: "rotateY(180deg)",
                  pointerEvents: activeTab === "signup" ? "auto" : "none",
                }}
              >
                <form onSubmit={(event) => event.preventDefault()}>
                  <p className="mb-5 text-center text-sm text-[#6f665c] sm:mb-[30px]">
                    Tạo tài khoản mới để bắt đầu với LawBot
                  </p>

                  <label className="mb-2 mt-4 block text-sm font-medium text-[#2f2923] sm:mb-[9px] sm:mt-[22px]">
                    Họ và tên
                  </label>
                  <div className="flex h-[50px] items-center gap-3 rounded-[9px] border border-[#eee4d7] bg-white px-[14px] transition-colors focus-within:border-[#e7bd67] focus-within:ring-2 focus-within:ring-[#e7bd67]/25 sm:h-[54px]">
                    <FieldIcon>
                      <User className="h-4 w-4" strokeWidth={2} />
                    </FieldIcon>
                    <input
                      type="text"
                      value={signupName}
                      onChange={(event) => setSignupName(event.target.value)}
                      placeholder="Nhập họ và tên của bạn"
                      className="w-full border-0 bg-transparent text-[#29231d] outline-none placeholder:text-[#9e958b]"
                    />
                  </div>

                  <EmailField value={signupEmail} onChange={setSignupEmail} />

                  <PasswordField
                    label="Mật khẩu"
                    value={signupPassword}
                    onChange={setSignupPassword}
                    placeholder="Tạo mật khẩu"
                    showPassword={showSignupPassword}
                    onToggle={() => setShowSignupPassword((prev) => !prev)}
                  />

                  <PasswordField
                    label="Xác nhận mật khẩu"
                    value={signupConfirmPassword}
                    onChange={setSignupConfirmPassword}
                    placeholder="Nhập lại mật khẩu"
                    showPassword={showSignupConfirmPassword}
                    onToggle={() =>
                      setShowSignupConfirmPassword((prev) => !prev)
                    }
                  />

                  <button
                    type="button"
                    className="mt-5 h-[52px] w-full rounded-[9px] border-0 text-base font-extrabold text-white bg-gradient-to-br from-[#e8bf73] to-[#b77519] shadow-[0_12px_26px_rgba(184,122,29,0.2)] transition-transform hover:-translate-y-px hover:shadow-[0_14px_30px_rgba(184,122,29,0.28)] cursor-pointer sm:mt-6 sm:h-14"
                  >
                    Đăng ký
                  </button>

                  <SocialButtons
                    isLoading={isLoading}
                    onLoadingChange={setIsLoading}
                    mode="signup"
                  />

                  <p className="mt-5 text-center text-sm text-[#8a8177] sm:mt-7">
                    Đã có tài khoản?{" "}
                    <button
                      type="button"
                      onClick={() => handleTabChange("login")}
                      className="border-0 bg-transparent p-0 font-bold text-[#9b6416] transition-colors hover:text-[#8b5517] cursor-pointer"
                    >
                      Đăng nhập ngay
                    </button>
                  </p>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>

      <LoadingOverlay isLoading={isLoading} />
    </main>
  );
};
