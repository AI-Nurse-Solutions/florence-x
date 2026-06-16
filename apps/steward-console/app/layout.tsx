import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Florence-X Steward Console",
  description: "The human authority interface. Humans decide. Nurses steward.",
};

const NAV = [
  { href: "/", label: "Review queue" },
  { href: "/incidents", label: "Incidents" },
  { href: "/registry", label: "Registry" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-gray-200 bg-white">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
              <Link href="/" className="font-semibold tracking-tight">
                Florence-X <span className="text-gray-400">· Steward Console</span>
              </Link>
              <nav className="flex gap-4 text-sm text-gray-600">
                {NAV.map((n) => (
                  <Link key={n.href} href={n.href} className="hover:text-gray-900">
                    {n.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
