"use client";

import { useEffect, useState } from "react";

/** Đọc localStorage key `userInfo` (JSON) và kiểm tra role admin. */
export function useIsAdminUser(): boolean {
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("userInfo");
      if (!raw) {
        setIsAdmin(false);
        return;
      }
      const parsed = JSON.parse(raw) as { role?: string };
      setIsAdmin(parsed?.role === "admin");
    } catch {
      setIsAdmin(false);
    }
  }, []);

  return isAdmin;
}
