import Cookies from "js-cookie";

const isBrowser = typeof window !== "undefined";

/**
 * Helper function to get token from cookies first, then fallback to localStorage
 */
export const getToken = (): string | undefined => {
  // In SSR, localStorage is unavailable; rely on cookies only
  if (!isBrowser) {
    return Cookies.get("token") || undefined;
  }

  return Cookies.get("token") || localStorage.getItem("token") || undefined;
};

/**
 * Helper function to check if current host is localhost or 127.0.0.1
 */
const isLocalhostOr127 = (): boolean => {
  if (typeof window === "undefined") return false;
  const hostname = window.location.hostname;
  return hostname === "localhost" || hostname === "127.0.0.1";
};

/**
 * Helper function to set token in both cookies and localStorage
 */
export const setToken = (token: string): void => {
  // For development/testing with ngrok, we need to adjust cookie settings
  const isLocalhost = isLocalhostOr127();
  const isNgrok =
    typeof window !== "undefined" && window.location.hostname.includes("ngrok");
  const isHttps =
    typeof window !== "undefined" && window.location.protocol === "https:";
  const hostname =
    typeof window !== "undefined" ? window.location.hostname : "";

  try {
    // IMPORTANT: Remove any existing token cookie first to avoid conflicts
    // On localhost/127.0.0.1, don't set domain attribute (it causes issues)
    // Just remove with path only
    Cookies.remove("token", { path: "/" });

    //console.log("Current hostname:", hostname);
    //console.log("Is HTTPS:", isHttps);

    // Determine cookie options based on environment
    const cookieOptions: Cookies.CookieAttributes = {
      path: "/",
      expires: 30, // 30 days
    };

    // For local development or HTTP, use less strict settings
    if (isLocalhost || !isHttps) {
      // Local or HTTP - no secure flag, lax sameSite
      // IMPORTANT: Don't set domain for localhost/127.0.0.1
      cookieOptions.sameSite = "lax";
    } else {
      // HTTPS environments - can use secure and none
      cookieOptions.secure = true;
      cookieOptions.sameSite = "none";
    }

    // Always set in localStorage first (works across localhost and 127.0.0.1)
    if (isBrowser) {
      localStorage.setItem("token", token);
    }

    //console.log("Setting token cookie with options:", cookieOptions);
    Cookies.set("token", token, cookieOptions);

    // Always set in localStorage as backup
    // localStorage.setItem("token", token);
    //console.log("Token set in cookies and localStorage:", token);
    //console.log("All cookies after setting:", Cookies.get());

    // Double-check if cookie was set
    setTimeout(() => {
      const tokenCookie = Cookies.get("token");
      //console.log("Token cookie after setting (delayed check):", tokenCookie);
      //console.log("All cookies after delay:", Cookies.get());
    }, 100);
  } catch (error) {
    //console.error("Error setting token cookie:", error);
  }
};

/**
 * Helper function to remove token from both cookies and localStorage
 */
export const removeToken = (): void => {
  if (isBrowser) {
    // Xóa từ localStorage trước
    localStorage.removeItem("token");

    // Xóa cookie với tất cả các options có thể
    // Xóa với path: "/"
    Cookies.remove("token", { path: "/" });
    // Xóa với path: "/" và domain: current domain
    const hostname = window.location.hostname;
    if (hostname) {
      Cookies.remove("token", { path: "/", domain: hostname });
      // Xóa với domain bắt đầu bằng dấu chấm (cho subdomain)
      if (
        !hostname.startsWith("localhost") &&
        !hostname.startsWith("127.0.0.1")
      ) {
        Cookies.remove("token", { path: "/", domain: `.${hostname}` });
      }
    }
    // Xóa không có domain (cho trường hợp cookie được set không có domain)
    Cookies.remove("token", { path: "/" });
  } else {
    // SSR: chỉ xóa với path
    Cookies.remove("token", { path: "/" });
  }
};

/**
 * Helper function to get user ID from cookies first, then fallback to localStorage
 */
export const getUserId = (): string | undefined => {
  if (!isBrowser) {
    return Cookies.get("user_id") || undefined;
  }

  return Cookies.get("user_id") || localStorage.getItem("user_id") || undefined;
};

/**
 * Helper function to set user ID in both cookies and localStorage
 */
export const setUserId = (userId: string): void => {
  // For development/testing with ngrok, we need to adjust cookie settings
  const isLocalhost = isLocalhostOr127();
  const isNgrok =
    typeof window !== "undefined" && window.location.hostname.includes("ngrok");
  const isHttps =
    typeof window !== "undefined" && window.location.protocol === "https:";
  const hostname =
    typeof window !== "undefined" ? window.location.hostname : "";

  try {
    // IMPORTANT: Remove any existing user_id cookie first to avoid conflicts
    // On localhost/127.0.0.1, don't set domain attribute
    Cookies.remove("user_id", { path: "/" });

    // Determine cookie options based on environment
    const cookieOptions: Cookies.CookieAttributes = {
      path: "/",
      expires: 30, // 30 days
    };

    // For local development or HTTP, use less strict settings
    if (isLocalhost || !isHttps) {
      // Local or HTTP - no secure flag, lax sameSite
      // IMPORTANT: Don't set domain for localhost/127.0.0.1
      cookieOptions.sameSite = "lax";
    } else {
      // HTTPS environments - can use secure and none
      cookieOptions.secure = true;
      cookieOptions.sameSite = "none";
    }

    //console.log("Setting user_id cookie with options:", cookieOptions);
    Cookies.set("user_id", userId, cookieOptions);

    // Always set in localStorage as backup
    // localStorage.setItem("user_id", userId);
    //console.log("User ID set in cookies and localStorage:", userId);
    //console.log("All cookies after setting user_id:", Cookies.get());
  } catch (error) {
    //console.error("Error setting user_id cookie:", error);
  }
};

/**
 * Helper function to remove user ID from both cookies and localStorage
 */
export const removeUserId = (): void => {
  // Remove cookie (don't set domain for localhost/127.0.0.1)
  Cookies.remove("user_id", { path: "/" });
  if (isBrowser) {
    localStorage.removeItem("user_id");
  }
};

/**
 * Helper function to get subscription status from cookies first, then fallback to localStorage
 */
export const getSubscriptionStatus = (): boolean => {
  const fromCookie = Cookies.get("subscriptionStatus");
  const fromLocalStorage = isBrowser
    ? localStorage.getItem("subscriptionStatus")
    : null;
  return fromCookie === "true" || fromLocalStorage === "true";
};

/**
 * Helper function to get subscription data from cookies first, then fallback to localStorage
 */
export const getSubscriptionData = (): any => {
  try {
    const fromCookie = Cookies.get("subscriptionData");
    const fromLocalStorage = isBrowser
      ? localStorage.getItem("subscriptionData")
      : null;

    const dataString = fromCookie || fromLocalStorage;
    return dataString ? JSON.parse(dataString) : null;
  } catch (error) {
    //console.error("Error retrieving subscription data:", error);
    return null;
  }
};

/**
 * Helper function to set subscription data in both cookies and localStorage
 */
export const setSubscriptionData = (isSubscribed: boolean, data: any): void => {
  // For development/testing with ngrok, we need to adjust cookie settings
  const isLocalhost = isLocalhostOr127();
  const isHttps =
    typeof window !== "undefined" && window.location.protocol === "https:";
  const hostname =
    typeof window !== "undefined" ? window.location.hostname : "";

  try {
    // Remove existing cookies first (don't set domain for localhost/127.0.0.1)
    Cookies.remove("subscriptionStatus", { path: "/" });
    Cookies.remove("subscriptionData", { path: "/" });
    Cookies.remove("subscriptionLastChecked", { path: "/" });

    // Determine cookie options based on environment
    const cookieOptions: Cookies.CookieAttributes = {
      path: "/",
      expires: 30, // 30 days
    };

    // For local development or HTTP, use less strict settings
    if (isLocalhost || !isHttps) {
      // Local or HTTP - no secure flag, lax sameSite
      // IMPORTANT: Don't set domain for localhost/127.0.0.1
      cookieOptions.sameSite = "lax";
    } else {
      // HTTPS environments - can use secure and none
      cookieOptions.secure = true;
      cookieOptions.sameSite = "none";
    }

    // //console.log("Setting subscription cookies with options:", cookieOptions);

    // Store in cookies
    Cookies.set(
      "subscriptionStatus",
      isSubscribed ? "true" : "false",
      cookieOptions
    );
    Cookies.set("subscriptionData", JSON.stringify(data), cookieOptions);
    Cookies.set(
      "subscriptionLastChecked",
      Date.now().toString(),
      cookieOptions
    );

    // Store in localStorage (browser only)
    if (isBrowser) {
      localStorage.setItem(
        "subscriptionStatus",
        isSubscribed ? "true" : "false"
      );
      localStorage.setItem("subscriptionData", JSON.stringify(data));
      localStorage.setItem("subscriptionLastChecked", Date.now().toString());
    }

    // //console.log("All cookies after setting subscription data:", Cookies.get());
  } catch (error) {
    //console.error("Error setting subscription cookies:", error);
  }
};

/**
 * Helper function to remove subscription data from both cookies and localStorage
 */
export const removeSubscriptionData = (): void => {
  // Remove from cookies (don't set domain for localhost/127.0.0.1)
  Cookies.remove("subscriptionStatus", { path: "/" });
  Cookies.remove("subscriptionData", { path: "/" });
  Cookies.remove("subscriptionLastChecked", { path: "/" });

  // Remove from localStorage
  if (isBrowser) {
    localStorage.removeItem("subscriptionStatus");
    localStorage.removeItem("subscriptionData");
    localStorage.removeItem("subscriptionLastChecked");
  }
};

/**
 * Helper function to create authorization header with Bearer token
 */
/**
 * Helper function to store user info in localStorage
 */
export const setUserInfo = (userInfo: any): void => {
  try {
    // localStorage.setItem("userInfo", JSON.stringify(userInfo));
    // IMPORTANT: Remove any existing userInfo cookie first to avoid conflicts
    // On localhost/127.0.0.1, don't set domain attribute
    Cookies.remove("userInfo", { path: "/" });

    const cookieOptions: Cookies.CookieAttributes = {
      path: "/",
      expires: 30, // 30 days
      sameSite: "lax",
    };
    Cookies.set("userInfo", JSON.stringify(userInfo), cookieOptions);
    // //console.log("User info stored in localStorage");
  } catch (error) {
    //console.error("Error storing user info:", error);
  }
};

/**
 * Helper function to get user info from localStorage
 */
export const getUserInfo = (): any => {
  try {
    // const userInfo = localStorage.getItem("userInfo");
    const userInfo = Cookies.get("userInfo");
    return userInfo ? JSON.parse(userInfo) : null;
  } catch (error) {
    //console.error("Error retrieving user info:", error);
    return null;
  }
};

/**
 * Helper function to remove user info from localStorage
 */
export const removeUserInfo = (): void => {
  // localStorage.removeItem("userInfo");
  // Remove cookie (don't set domain for localhost/127.0.0.1)
  Cookies.remove("userInfo", { path: "/" });
};

export const createAuthHeader = (): { Authorization: string } | undefined => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : undefined;
};

export const getUserIdFromCookie = (): string | undefined => {
  const userId = Cookies.get("user_id");
  //console.log("[getUserIdFromCookie] userId:", userId);
  return userId || undefined;
};
