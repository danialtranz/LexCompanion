import { useState } from "react";
import { Header } from "./Header";
import { GoogleSignInButton } from "./GoogleSignInButton";

import { LoadingOverlay } from "./LoadingOverlay";
import { Terms } from "./Terms";

export const SiginInView = () => {
  const [activeTab] = useState<"login" | "signup">("login");
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 md:p-8 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 z-0"></div>
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-to-br from-pink-500/10 to-rose-500/10 rounded-full blur-[80px] translate-y-1/2 -translate-x-1/2 z-0"></div>

      <div className="relative z-10 w-full max-w-[480px] bg-white rounded-2xl shadow-xl p-6 md:p-12">
        <Header />

        <div className="w-full">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              {activeTab === "login" ? "Đăng nhập" : "Đăng ký"}
            </h1>
            <p className="text-gray-600">
              {activeTab === "login"
                ? "Sẵn sàng với hành trình của bạn"
                : "Tạo tài khoản mới để bắt đầu"}
            </p>
          </div>

          <GoogleSignInButton
            disabled={isLoading}
            onLoadingChange={setIsLoading}
          />

          <Terms />
        </div>
      </div>

      <LoadingOverlay isLoading={isLoading} />
    </div>
  );
};
