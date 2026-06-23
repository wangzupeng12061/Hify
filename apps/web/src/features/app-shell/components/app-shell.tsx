import type { ReactNode } from "react";

const NAVIGATION_ITEMS = [
  "Identity",
  "Providers",
  "Agents",
  "Runs",
  "Knowledge",
  "Usage",
];

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
        <nav className="app-shell__nav">
          {NAVIGATION_ITEMS.map((item) => (
            <a
              aria-current={item === "Identity" ? "page" : undefined}
              className="app-shell__nav-link"
              href={item === "Identity" ? "/" : "#"}
              key={item}
            >
              {item}
            </a>
          ))}
        </nav>
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
