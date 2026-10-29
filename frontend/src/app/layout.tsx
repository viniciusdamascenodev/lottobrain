import type { Metadata } from "next";
import "@/design-system/tokens.css";

export const metadata: Metadata = {
  title: "LottoBrain",
  description: "Plataforma privada de análise de loterias.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
