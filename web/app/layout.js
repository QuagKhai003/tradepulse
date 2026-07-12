/**
 * layout.js — root layout (plan §10.4: Vietnamese default).
 * @context  Two-role type system: Plus Jakarta Sans = body/labels (text role); Be Vietnam Pro =
 *           headings + data numerals (display role). Both carry the Vietnamese subset, both humanist
 *           (no monospace/terminal look). Hierarchy comes from a fixed 4-5 step size scale + weight.
 * @affects  All routes.
 */
import { Plus_Jakarta_Sans, Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";

const sans = Plus_Jakarta_Sans({
  subsets: ["latin", "vietnamese"],
  variable: "--font-sans",
  display: "swap",
  weight: ["400", "600", "700"],   // 500 dropped — only .permo used it and 400 covers it
});
const display = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  variable: "--font-display",
  display: "swap",
  weight: ["600", "700", "800"],
});

export const metadata = {
  title: "TradePulse — Ra-đa nhu cầu xuất khẩu",
  description: "Nhu cầu thế giới đang dịch chuyển ở đâu — cho nhà xuất khẩu Việt Nam.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="vi" className={`${sans.variable} ${display.variable}`}>
      <body>{children}</body>
    </html>
  );
}
