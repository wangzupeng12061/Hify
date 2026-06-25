"use client";

import { useState, type ReactNode } from "react";

import { SettingsDialog } from "@/features/settings";

import { AppNavigation } from "./app-navigation";
import { AppShellMode } from "./app-shell-mode";

export function AppShell({ children }: { children: ReactNode }) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

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
        <div className="app-shell__sidebar-footer">
          <button
            className="app-shell__settings-button"
            onClick={() => setIsSettingsOpen(true)}
            type="button"
          >
            Settings
          </button>
        </div>
      </aside>
      <div className="app-shell__main">
        <header className="app-shell__header">
          <AppShellMode />
        </header>
        <main className="app-shell__content">{children}</main>
      </div>
      <SettingsDialog isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
}
