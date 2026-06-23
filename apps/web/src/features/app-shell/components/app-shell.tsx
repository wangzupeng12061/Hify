import type { ReactNode } from "react";

import { AppNavigation } from "./app-navigation";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="app-shell__sidebar" aria-label="Primary navigation">
        <div className="app-shell__brand">
          <span className="app-shell__logo">H</span>
          <div>
            <strong>Hify</strong>
            <span>AI Agent Platform</span>
          </div>
        </div>
        <AppNavigation />
      </aside>
      <div className="app-shell__main">
        <header className="app-shell__header">
          <div>
            <p className="app-shell__eyebrow">Phase One</p>
            <h1>Team Agent Workspace</h1>
          </div>
          <div className="app-shell__environment">Online</div>
        </header>
        <main className="app-shell__content">{children}</main>
      </div>
    </div>
  );
}
