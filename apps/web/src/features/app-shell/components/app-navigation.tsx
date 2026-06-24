"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavigationItem = {
  href: string;
  label: string;
};

const USER_NAVIGATION_ITEMS: NavigationItem[] = [
  { href: "/chat", label: "Chat" },
  { href: "/conversations", label: "History" },
];

const ADMIN_NAVIGATION_ITEMS: NavigationItem[] = [
  { href: "/admin/agents", label: "Agents" },
  { href: "/admin/knowledge", label: "Knowledge" },
  { href: "/admin/providers", label: "Providers" },
  { href: "/admin/tools", label: "Tools" },
  { href: "/admin/mcp", label: "MCP" },
  { href: "/admin/workflows", label: "Workflows" },
  { href: "/admin/usage", label: "Usage" },
  { href: "/admin/runs", label: "Diagnostics" },
];

export function AppNavigation() {
  const pathname = usePathname();
  const isAdmin = pathname.startsWith("/admin");
  const primaryItems = isAdmin ? ADMIN_NAVIGATION_ITEMS : USER_NAVIGATION_ITEMS;
  const switchItem = isAdmin
    ? { href: "/chat", label: "User Workspace" }
    : { href: "/admin/agents", label: "Admin Console" };

  return (
    <nav className="app-shell__nav" aria-label={isAdmin ? "Admin navigation" : "User navigation"}>
      <p className="app-shell__nav-label">{isAdmin ? "Admin Console" : "User Workspace"}</p>
      {primaryItems.map((item) => (
        <NavigationLink item={item} key={item.label} pathname={pathname} />
      ))}
      <div className="app-shell__nav-divider" />
      <NavigationLink item={switchItem} pathname={pathname} />
    </nav>
  );
}

function NavigationLink({ item, pathname }: { item: NavigationItem; pathname: string }) {
  const isCurrent = pathname === item.href || pathname.startsWith(`${item.href}/`);

  return (
    <Link
      aria-current={isCurrent ? "page" : undefined}
      className="app-shell__nav-link"
      href={item.href}
    >
      {item.label}
    </Link>
  );
}
