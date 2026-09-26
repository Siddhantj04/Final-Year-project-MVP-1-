"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    const token = localStorage.getItem("rl_token");
    router.replace(token ? "/dashboard" : "/login");
  }, [router]);
  return <LoadingSpinner label="Redirecting..." />;
}
