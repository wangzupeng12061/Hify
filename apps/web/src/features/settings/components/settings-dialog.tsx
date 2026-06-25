"use client";

import { useMemo, useState } from "react";

import { useAgents, type Agent } from "@/features/agents";

import { useLocalSettings } from "../hooks";
import type { HifyLanguagePreference, HifyThemePreference } from "../types";

type SettingsTab = "general" | "chat" | "notifications" | "account";

const SETTINGS_TABS: Array<{ id: SettingsTab; label: string }> = [
  { id: "general", label: "通用" },
  { id: "chat", label: "Chat" },
  { id: "notifications", label: "通知" },
  { id: "account", label: "账户" },
];

const EMPTY_AGENTS: Agent[] = [];

export function SettingsDialog({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  if (!isOpen) {
    return null;
  }

  return <SettingsDialogContent onClose={onClose} />;
}

function SettingsDialogContent({ onClose }: { onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const { resetSettings, settings, updateSettings } = useLocalSettings();
  const agentsQuery = useAgents();
  const agents = agentsQuery.data ?? EMPTY_AGENTS;
  const runnableAgents = useMemo(() => getRunnableAgents(agents), [agents]);

  return (
    <div className="settings-overlay" role="presentation">
      <section
        aria-label="Settings"
        aria-modal="true"
        className="settings-dialog"
        role="dialog"
      >
        <aside className="settings-dialog__sidebar">
          <button
            aria-label="Close settings"
            className="settings-dialog__close"
            onClick={onClose}
            type="button"
          >
            ×
          </button>
          <div className="settings-dialog__profile">
            <span>H</span>
            <div>
              <strong>Hify User</strong>
              <small>Local preferences</small>
            </div>
          </div>
          <nav className="settings-dialog__nav" aria-label="Settings sections">
            {SETTINGS_TABS.map((tab) => (
              <button
                data-active={activeTab === tab.id}
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                type="button"
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <button className="settings-dialog__reset" onClick={resetSettings} type="button">
            Reset local settings
          </button>
        </aside>
        <div className="settings-dialog__content">
          {activeTab === "general" ? (
            <GeneralSettings
              language={settings.language}
              theme={settings.theme}
              onLanguageChange={(language) => updateSettings({ language })}
              onThemeChange={(theme) => updateSettings({ theme })}
            />
          ) : null}
          {activeTab === "chat" ? (
            <ChatSettings
              autoScroll={settings.autoScroll}
              defaultAgentId={settings.defaultAgentId}
              runnableAgents={runnableAgents}
              showToolActivity={settings.showToolActivity}
              onAutoScrollChange={(autoScroll) => updateSettings({ autoScroll })}
              onDefaultAgentChange={(defaultAgentId) => updateSettings({ defaultAgentId })}
              onShowToolActivityChange={(showToolActivity) => updateSettings({ showToolActivity })}
            />
          ) : null}
          {activeTab === "notifications" ? (
            <NotificationSettings
              browserNotifications={settings.browserNotifications}
              onBrowserNotificationsChange={(browserNotifications) =>
                updateSettings({ browserNotifications })
              }
            />
          ) : null}
          {activeTab === "account" ? <AccountSettings /> : null}
        </div>
      </section>
    </div>
  );
}

function GeneralSettings({
  language,
  theme,
  onLanguageChange,
  onThemeChange,
}: {
  language: HifyLanguagePreference;
  theme: HifyThemePreference;
  onLanguageChange: (language: HifyLanguagePreference) => void;
  onThemeChange: (theme: HifyThemePreference) => void;
}) {
  return (
    <div className="settings-panel">
      <h2>通用</h2>
      <SettingsSelect
        description="第一版只保存本地偏好，不会同步到服务器。"
        label="语言"
        onChange={(value) => onLanguageChange(value as HifyLanguagePreference)}
        options={[
          { label: "简体中文", value: "zh-CN" },
          { label: "English", value: "en-US" },
          { label: "跟随系统", value: "system" },
        ]}
        value={language}
      />
      <div className="settings-field">
        <div>
          <strong>主题</strong>
          <p>控制 Hify 本地显示主题。</p>
        </div>
        <div className="settings-theme-grid">
          {[
            { label: "浅色", value: "light" },
            { label: "深色", value: "dark" },
            { label: "自动", value: "system" },
          ].map((option) => (
            <button
              data-active={theme === option.value}
              key={option.value}
              onClick={() => onThemeChange(option.value as HifyThemePreference)}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ChatSettings({
  autoScroll,
  defaultAgentId,
  runnableAgents,
  showToolActivity,
  onAutoScrollChange,
  onDefaultAgentChange,
  onShowToolActivityChange,
}: {
  autoScroll: boolean;
  defaultAgentId: string | null;
  runnableAgents: Agent[];
  showToolActivity: boolean;
  onAutoScrollChange: (value: boolean) => void;
  onDefaultAgentChange: (agentId: string | null) => void;
  onShowToolActivityChange: (value: boolean) => void;
}) {
  return (
    <div className="settings-panel">
      <h2>Chat</h2>
      <SettingsSelect
        description="打开新聊天时默认选择的已发布 Agent。"
        label="默认 Agent"
        onChange={(value) => onDefaultAgentChange(value || null)}
        options={[
          { label: "自动选择", value: "" },
          ...runnableAgents.map((agent) => ({
            label: `${agent.name} · v${agent.latest_version_number}`,
            value: agent.id,
          })),
        ]}
        value={defaultAgentId ?? ""}
      />
      <SettingsToggle
        checked={showToolActivity}
        description="在聊天消息流中展示工具调用、参数和结果状态。"
        label="显示工具调用过程"
        onChange={onShowToolActivityChange}
      />
      <SettingsToggle
        checked={autoScroll}
        description="Agent 回复时自动滚动到最新消息。"
        label="自动滚动到最新"
        onChange={onAutoScrollChange}
      />
    </div>
  );
}

function NotificationSettings({
  browserNotifications,
  onBrowserNotificationsChange,
}: {
  browserNotifications: boolean;
  onBrowserNotificationsChange: (value: boolean) => void;
}) {
  return (
    <div className="settings-panel">
      <h2>通知</h2>
      <SettingsToggle
        checked={browserNotifications}
        description="第一版只保存开关，后续接入 Notification API。"
        label="浏览器通知"
        onChange={onBrowserNotificationsChange}
      />
    </div>
  );
}

function AccountSettings() {
  return (
    <div className="settings-panel">
      <h2>账户</h2>
      <div className="settings-field">
        <div>
          <strong>登录方式</strong>
          <p>生产环境通过 Cloudflare Access 认证。账户资料后续从身份模块读取。</p>
        </div>
        <span className="settings-pill">Cloudflare Access</span>
      </div>
    </div>
  );
}

function SettingsSelect({
  description,
  label,
  onChange,
  options,
  value,
}: {
  description: string;
  label: string;
  onChange: (value: string) => void;
  options: Array<{ label: string; value: string }>;
  value: string;
}) {
  return (
    <label className="settings-field">
      <div>
        <strong>{label}</strong>
        <p>{description}</p>
      </div>
      <select
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.map((option) => (
          <option key={`${option.value}:${option.label}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function SettingsToggle({
  checked,
  description,
  label,
  onChange,
}: {
  checked: boolean;
  description: string;
  label: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="settings-field settings-field--toggle">
      <div>
        <strong>{label}</strong>
        <p>{description}</p>
      </div>
      <input
        aria-label={label}
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
    </label>
  );
}

function getRunnableAgents(agents: Agent[]): Agent[] {
  return agents.filter(
    (agent) => agent.status === "published" && agent.latest_version_number > 0,
  );
}
