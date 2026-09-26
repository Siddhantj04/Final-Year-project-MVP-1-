"use client";

import ErrorAlert from "@/components/ErrorAlert";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ApiError, apiFetch, setAuth } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

type TokenResponse = {
  access_token: string;
  role: string;
  email: string;
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  function validate() {
    const next: { email?: string; password?: string } = {};
    if (!email.trim()) next.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next.email = "Enter a valid email address.";
    if (!password) next.password = "Password is required.";
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!validate()) return;
    setLoading(true);
    try {
      const data = await apiFetch<TokenResponse>(
        "/auth/login",
        { method: "POST", body: JSON.stringify({ email: email.trim(), password }) },
        false,
      );
      setAuth(data.access_token, data.role, data.email);
      router.push(data.role === "admin" ? "/admin" : "/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-2">Sign in</h1>
      <p className="mb-6 text-body">RadiologyLearn AI — educational workflow support only.</p>
      <div className="card space-y-4">
        {loading && <LoadingSpinner label="Signing in..." />}
        {!loading && (
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <ErrorAlert message={error} />
            <div>
              <label className="label-text" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                className="input-field"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              {fieldErrors.email && <p className="mt-1 text-sm text-red-600">{fieldErrors.email}</p>}
            </div>
            <div>
              <label className="label-text" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                className="input-field"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {fieldErrors.password && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.password}</p>
              )}
            </div>
            <button type="submit" className="btn-primary w-full">
              Sign in
            </button>
          </form>
        )}
        <p className="text-center text-sm text-body">
          No account?{" "}
          <Link href="/register" className="font-medium text-black underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
