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

  return <SiginInView />;
};

export default SiginIn;
