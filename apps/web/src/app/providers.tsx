"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { createHifyQueryClient } from "@/lib/query/query-client";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createHifyQueryClient);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
