import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/features/app-shell";

import { AppProviders } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hify",
  description: "Internal AI agent platform",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppProviders>
          <AppShell>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
