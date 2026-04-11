/* eslint-disable */
"use client";

import { useState, useEffect } from "react";
import { SiginInView } from "../views/signIn/index";
// neu user da dang nhap thi redirect ve trang chu
import { useRouter } from "next/navigation";
import { getToken } from "../utils/tokenManager";
import { LoadingOverlay } from "../components/LoadingLoginOverlay";
const SiginIn = () => {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState<boolean>(true);

  //   useEffect(() => {
  //     // Check token synchronously from localStorage/cookie first (fast)
  //     const token = getToken();

  //     if (token) {
  //       // If token exists, redirect immediately without waiting
  //       router.push("/");
  //       return;
  //     }

  //     // Nếu không có token, cho phép render trang login
  //     setIsChecking(false);
  //   }, [router]);

  //   // Chờ check token xong mới render (tránh flash trang login)
  //   if (isChecking) {
  //     return <LoadingOverlay isLoading={true} />;
  //   }

  return <SiginInView />;
};

export default SiginIn;
