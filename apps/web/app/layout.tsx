import type { Metadata } from "next";
import localFont from "next/font/local";
import { Providers } from "@/components/providers";
import "./globals.css";

// Satoshi (Indian Type Foundry, licence Fontshare), auto-hébergée, pour tout le site : une seule famille.
const satoshi = localFont({
  src: "./fonts/Satoshi-Variable.woff2",
  weight: "300 900",
  variable: "--font-satoshi",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Meridian — GEO",
  description: "Suivez la visibilité de votre marque dans les moteurs génératifs.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning : la landing pose la classe lp-motion sur <html> avant l'hydratation (app/(site)/layout.tsx).
    <html lang="fr" className={`${satoshi.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
