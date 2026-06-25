export type HifyThemePreference = "light" | "dark" | "system";
export type HifyLanguagePreference = "zh-CN" | "en-US" | "system";

export type HifyLocalSettings = {
  autoScroll: boolean;
  browserNotifications: boolean;
  defaultAgentId: string | null;
  language: HifyLanguagePreference;
  showToolActivity: boolean;
  theme: HifyThemePreference;
};
