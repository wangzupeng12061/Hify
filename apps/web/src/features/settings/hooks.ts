"use client";

import { useCallback, useEffect, useMemo, useSyncExternalStore } from "react";

import type { HifyLocalSettings } from "./types";

const SETTINGS_STORAGE_KEY = "hify.localSettings";

const defaultSettings: HifyLocalSettings = {
  autoScroll: true,
  browserNotifications: false,
  defaultAgentId: null,
  language: "system",
  showToolActivity: true,
  theme: "system",
};

let cachedSettings: HifyLocalSettings = defaultSettings;
const listeners = new Set<() => void>();

export function useLocalSettings() {
  const settings = useSyncExternalStore(subscribeSettings, getSettingsSnapshot, getServerSnapshot);

  useEffect(() => {
    loadSettingsFromStorage();
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme(settings.theme);
  }, [settings.theme]);

  const updateSettings = useCallback((partialSettings: Partial<HifyLocalSettings>) => {
    saveSettings({
      ...cachedSettings,
      ...partialSettings,
    });
  }, []);

  const resetSettings = useCallback(() => {
    saveSettings(defaultSettings);
  }, []);

  return useMemo(
    () => ({
      resetSettings,
      settings,
      updateSettings,
    }),
    [resetSettings, settings, updateSettings],
  );
}

function subscribeSettings(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSettingsSnapshot(): HifyLocalSettings {
  return cachedSettings;
}

function getServerSnapshot(): HifyLocalSettings {
  return defaultSettings;
}

function loadSettingsFromStorage() {
  if (typeof window === "undefined") {
    return;
  }

  cachedSettings = readSettings();
  notifyListeners();
}

function saveSettings(settings: HifyLocalSettings) {
  cachedSettings = normalizeSettings(settings);
  if (typeof window !== "undefined") {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(cachedSettings));
  }
  notifyListeners();
}

function readSettings(): HifyLocalSettings {
  if (typeof window === "undefined") {
    return defaultSettings;
  }

  const rawSettings = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
  if (rawSettings === null) {
    return defaultSettings;
  }

  try {
    const parsedSettings: unknown = JSON.parse(rawSettings);
    if (!isSettingsRecord(parsedSettings)) {
      return defaultSettings;
    }
    return normalizeSettings({
      ...defaultSettings,
      ...parsedSettings,
    });
  } catch {
    return defaultSettings;
  }
}

function normalizeSettings(settings: HifyLocalSettings): HifyLocalSettings {
  return {
    autoScroll: Boolean(settings.autoScroll),
    browserNotifications: Boolean(settings.browserNotifications),
    defaultAgentId: settings.defaultAgentId || null,
    language: ["zh-CN", "en-US", "system"].includes(settings.language)
      ? settings.language
      : defaultSettings.language,
    showToolActivity: Boolean(settings.showToolActivity),
    theme: ["light", "dark", "system"].includes(settings.theme)
      ? settings.theme
      : defaultSettings.theme,
  };
}

function isSettingsRecord(value: unknown): value is HifyLocalSettings {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function notifyListeners() {
  listeners.forEach((listener) => listener());
}

function resolvedTheme(theme: HifyLocalSettings["theme"]): "light" | "dark" | "system" {
  if (theme !== "system") {
    return theme;
  }
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "system";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
