"use client";

import ErrorAlert from "@/components/ErrorAlert";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ApiError, apiFetch } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  function validate() {
    const next: Record<string, string> = {};
    if (!email.trim()) next.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next.email = "Enter a valid email address.";
    if (password.length < 8) next.password = "Password must be at least 8 characters.";
    else if (!/[A-Za-z]/.test(password) || !/\d/.test(password))
      next.password = "Password must include at least one letter and one number.";
    if (password !== confirm) next.confirm = "Passwords do not match.";
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!validate()) return;
    setLoading(true);
    try {
      await apiFetch(
        "/auth/register",
        {
          method: "POST",
          body: JSON.stringify({ email: email.trim(), password, role: "reviewer" }),
        },
        false,
      );
      router.push("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-2">Create account</h1>
      <p className="mb-6 text-body">Reviewer registration for educational use.</p>
      <div className="card space-y-4">
        {loading && <LoadingSpinner label="Creating account..." />}
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
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {fieldErrors.password && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.password}</p>
              )}
            </div>
            <div>
              <label className="label-text" htmlFor="confirm">
                Confirm password
              </label>
              <input
                id="confirm"
                className="input-field"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
              {fieldErrors.confirm && <p className="mt-1 text-sm text-red-600">{fieldErrors.confirm}</p>}
            </div>
            <button type="submit" className="btn-primary w-full">
              Register
            </button>
          </form>
        )}
        <p className="text-center text-sm text-body">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-black underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
