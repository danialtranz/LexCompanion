import { useEffect, useRef } from "react";
import { useRouter } from "next/router";
import Image from "next/image";
import { IMAGES } from "../../../configs/images";
import toast from "react-hot-toast";
import { PAGES_ID } from "../../../configs/menu";
import { useSignInGoogle } from "@/hooks/useUserHook";

export default function GoogleCallback() {
  const router = useRouter();
  const errorOccurredMessage = "An error occurred";

  const { login } = useSignInGoogle();
  const hasProcessed = useRef(false);

  useEffect(() => {
    const handleGoogleLogin = async () => {
      // Prevent multiple calls
      if (hasProcessed.current) {
        //console.log("[Google Callback] Đã xử lý rồi, bỏ qua");
        return;
      }
      const google_redirect_uri = `${process.env.NEXT_PUBLIC_GOOGLE_OAUTH2_CALLBACK}`;
      const code = Array.isArray(router.query.code)
        ? router.query.code[0]
        : router.query.code || "";

      if (code) {
        hasProcessed.current = true; // Mark as processed
        try {
          const errCode = await login({ code, google_redirect_uri });
          console.log("[Google Callback] Kết quả từ login:", errCode);

          if (errCode === 0) {
            router.push("/chat");
          } else {
            toast.error(errorOccurredMessage);
            router.push("/sign-in");
          }
        } catch {
          toast.error(errorOccurredMessage);
          router.push(PAGES_ID.sign_in);
        }
      } else {
        hasProcessed.current = true; // Mark as processed

        localStorage.clear(); // Clear all stored data
        toast.error(errorOccurredMessage);
        router.push(PAGES_ID.sign_in);
      }
    };

    if (router.isReady) {
      handleGoogleLogin();
    }
  }, [router.isReady, router.query.code, login, router, errorOccurredMessage]);

  const loadingStyles = `
    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #4facfe 75%, #00f2fe 100%);
      background-size: 400% 400%;
      animation: gradientShift 8s ease infinite;
      position: relative;
      overflow: hidden;
    }
    
    .loading-container::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
      pointer-events: none;
    }
    
    .loading-content {
      position: relative;
      z-index: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    
    .loading-title {
      color: white;
      font-size: 28px;
      font-weight: 600;
      margin-bottom: 12px;
      text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    
    .loading-text {
      color: rgba(255, 255, 255, 0.9);
      font-size: 16px;
      font-weight: 400;
      margin-top: 8px;
      text-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
    }
    
    .avatar-container {
      position: relative;
      width: 120px;
      height: 120px;
      margin-bottom: 24px;
    }
    
    .avatar-wrapper {
      width: 100%;
      height: 100%;
      position: relative;
      animation: float 3s ease-in-out infinite;
    }
    
    .avatar-image {
      width: 100%;
      height: 100%;
      object-fit: contain;
      border-radius: 50%;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
      animation: moveAround 4s ease-in-out infinite;
    }
    
    @keyframes gradientShift {
      0% {
        background-position: 0% 50%;
      }
      50% {
        background-position: 100% 50%;
      }
      100% {
        background-position: 0% 50%;
      }
    }
    
    @keyframes float {
      0%, 100% {
        transform: translateY(0px);
      }
      50% {
        transform: translateY(-20px);
      }
    }
    
    @keyframes moveAround {
      0% {
        transform: translate(0, 0) scale(1);
      }
      25% {
        transform: translate(15px, -15px) scale(1.05);
      }
      50% {
        transform: translate(-10px, -25px) scale(1);
      }
      75% {
        transform: translate(-15px, 10px) scale(1.05);
      }
      100% {
        transform: translate(0, 0) scale(1);
      }
    }
  `;

  const redirectingText = "Redirecting";
  const pleaseWaitText = "You are being redirected, please wait...";

  return (
    <div className="loading-container">
      <style>{loadingStyles}</style>
      <div className="loading-content">
        <div className="avatar-container">
          <div className="avatar-wrapper">
            <Image
              src={IMAGES.lexCompanion.logo}
              alt="Lex Companion Avatar"
              width={120}
              height={120}
              className="avatar-image"
              priority
            />
          </div>
        </div>
        <div className="loading-title">{redirectingText}</div>
        <div className="loading-text">{pleaseWaitText}</div>
      </div>
    </div>
  );
}
