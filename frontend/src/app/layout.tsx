import type { Metadata } from "next";
import AppNav from "@/components/AppNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "RadiologyLearn AI",
  description: "Explainable chest X-ray analysis for education and research only.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppNav />
        <main className="mx-auto min-h-[calc(100vh-4rem)] max-w-6xl px-4 py-8">{children}</main>
        <footer className="border-t border-gray-200 py-4 text-center text-sm text-body">
          For education and research use only — not for clinical diagnosis.
        </footer>
      </body>
    </html>
  );
}
