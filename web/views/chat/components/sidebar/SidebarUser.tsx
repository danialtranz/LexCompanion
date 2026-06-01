"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/utils/tokenManager";

type StoredUserInfo = {
  name?: string;
  email?: string;
  picture?: string;
  id?: string;
  role?: string;
};

const NAME_MAX_LEN = 22;

function parseUserInfo(raw: string | null): StoredUserInfo | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredUserInfo;
    if (!parsed?.name && !parsed?.email) return null;
    return parsed;
  } catch {
    return null;
  }
}

function truncateName(name: string, maxLen = NAME_MAX_LEN): string {
  const s = name.trim();
  if (s.length <= maxLen) return s;
  return `${s.slice(0, maxLen - 1)}…`;
}

function readStoredUser(): StoredUserInfo | null {
  if (typeof window === "undefined") return null;
  if (!getToken()) return null;
  return parseUserInfo(localStorage.getItem("userInfo"));
}

function avatarInitial(user: StoredUserInfo): string {
  const fromName = user.name?.trim().charAt(0);
  if (fromName) return fromName.toUpperCase();
  const fromEmail = user.email?.trim().charAt(0);
  if (fromEmail) return fromEmail.toUpperCase();
  return "?";
}

export const SidebarUser = () => {
  const [user, setUser] = useState<StoredUserInfo | null>(null);
  const [avatarError, setAvatarError] = useState(false);

  useEffect(() => {
    setUser(readStoredUser());
  }, []);

  const showAvatarImage = Boolean(user?.picture) && !avatarError;
  const displayLabel = user?.name?.trim() || user?.email?.trim() || "Người dùng";
  const email = user?.email?.trim() ?? "";

  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-[#ebe3d6] bg-white px-3 py-2.5">
      {showAvatarImage ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={user!.picture}
          src={user!.picture}
          alt=""
          width={36}
          height={36}
          className="h-9 w-9 shrink-0 rounded-full object-cover ring-1 ring-[#ebe3d6]"
          onError={() => setAvatarError(true)}
        />
      ) : (
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#d4a96a] to-[#9a6c2b] text-sm font-semibold text-white">
          {user ? avatarInitial(user) : "?"}
        </div>
      )}
      <div className="min-w-0 flex-1 text-left">
        <b
          className="block truncate text-xs font-semibold text-[#2c2620]"
          title={user ? displayLabel : undefined}
        >
          {user ? truncateName(displayLabel) : "Khách"}
        </b>
        <span
          className="block truncate text-[10px] text-[#8a8178]"
          title={email || undefined}
        >
          {user ? email || "—" : "Chưa đăng nhập"}
        </span>
      </div>
    </div>
  );
};
