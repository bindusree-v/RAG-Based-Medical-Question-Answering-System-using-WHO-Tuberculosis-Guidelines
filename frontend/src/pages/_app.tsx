import type { AppProps } from "next/app";
import { Toaster } from "react-hot-toast";
import "@/styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Component {...pageProps} />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: "#1a1d27",
            color: "#e8eaf0",
            border: "1px solid #2a2d3e",
            fontSize: "13px",
          },
        }}
      />
    </>
  );
}
