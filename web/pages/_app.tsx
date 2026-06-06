import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { I18nProvider } from "@/locale/I18nProvider";

export default function App({ Component, pageProps }: AppProps) {
  const queryClient = new QueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <Component {...pageProps} />
        <Toaster position="top-center" toastOptions={{ duration: 4000 }} />
      </I18nProvider>
    </QueryClientProvider>
  );
}
