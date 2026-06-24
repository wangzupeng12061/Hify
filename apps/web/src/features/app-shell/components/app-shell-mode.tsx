"use client";

import { usePathname } from "next/navigation";

export function AppShellMode() {
  const pathname = usePathname();
  const isAdmin = pathname.startsWith("/admin");

  return (
    <>
      <div>
        <p className="app-shell__eyebrow">Phase One</p>
        <h1>{isAdmin ? "Admin Console" : "User Workspace"}</h1>
      </div>
      <div className="app-shell__environment">{isAdmin ? "Management" : "Chat"}</div>
    </>
  );
}
