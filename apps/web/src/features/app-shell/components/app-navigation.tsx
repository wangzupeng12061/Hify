"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAVIGATION_ITEMS = [
  { href: "/", label: "Identity" },
  { href: "/providers", label: "Providers" },
  { href: "/agents", label: "Agents" },
  { href: "/conversations", label: "Conversations" },
  { href: "/runs", label: "Runs" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "#", label: "Usage" },
];

export function AppNavigation() {
  const pathname = usePathname();

  return (
    <nav className="app-shell__nav">
      {NAVIGATION_ITEMS.map((item) => {
        const isCurrent =
          item.href !== "#" &&
          (pathname === item.href || pathname.startsWith(`${item.href}/`));

        return (
          <Link
            aria-current={isCurrent ? "page" : undefined}
            className="app-shell__nav-link"
            href={item.href}
            key={item.label}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
