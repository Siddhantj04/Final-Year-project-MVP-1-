"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearAuth, getAuthRole } from "@/lib/api";
import { useEffect, useState } from "react";

const links = [
  { href: "/upload", label: "Upload", roles: ["reviewer", "admin"] },
  { href: "/dashboard", label: "Reviewer Dashboard", roles: ["reviewer", "admin"] },
  { href: "/admin", label: "Admin", roles: ["admin"] },
];

export default function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    setRole(getAuthRole());
  }, [pathname]);

  if (pathname === "/login" || pathname === "/register") return null;

  function logout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4">
        <Link href="/dashboard" className="text-lg font-bold text-black">
          RadiologyLearn AI
        </Link>
        <nav className="flex flex-wrap items-center gap-2">
          {links
            .filter((l) => !role || l.roles.includes(role))
            .map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${
                  pathname.startsWith(l.href) ? "bg-powder text-black" : "text-body hover:bg-gray-100"
                }`}
              >
                {l.label}
              </Link>
            ))}
          <button type="button" onClick={logout} className="btn-primary text-sm">
            Log out
          </button>
        </nav>
      </div>
    </header>
  );
}
