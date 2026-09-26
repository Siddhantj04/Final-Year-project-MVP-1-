"use client";

import AuthGuard from "@/components/AuthGuard";
import ErrorAlert from "@/components/ErrorAlert";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ApiError, apiFetch, getAuthRole } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type AdminMetrics = {
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  specificity: number | null;
  f1_score: number | null;
  roc_auc: number | null;
  confusion_matrix: number[][] | null;
  workflow_stats: {
    total_cases: number;
    pending_review: number;
    approved: number;
    rejected: number;
    cases_by_status: Record<string, number>;
  };
};

export default function AdminPage() {
  return (
    <AuthGuard>
      <AdminContent />
    </AuthGuard>
  );
}

function AdminContent() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);

  useEffect(() => {
    const role = getAuthRole();
    if (role !== "admin") {
      router.replace("/dashboard");
      return;
    }
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await apiFetch<AdminMetrics>("/admin/metrics");
        setMetrics(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load admin metrics.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  const cm = metrics?.confusion_matrix ?? [
    [0, 0],
    [0, 0],
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1>Admin dashboard</h1>
        <p className="mt-2 text-body">Model performance metrics and workflow statistics.</p>
      </div>
      <ErrorAlert message={error} />
      {loading && <LoadingSpinner label="Loading metrics..." />}
      {!loading && metrics && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["Accuracy", metrics.accuracy],
              ["Precision", metrics.precision],
              ["Recall", metrics.recall],
              ["Specificity", metrics.specificity],
              ["F1 score", metrics.f1_score],
              ["ROC AUC", metrics.roc_auc],
            ].map(([label, value]) => (
              <div key={String(label)} className="card">
                <h3 className="text-lg">{label}</h3>
                <p className="mt-2 text-2xl font-bold text-black">
                  {value != null ? `${(Number(value) * 100).toFixed(2)}%` : "N/A"}
                </p>
              </div>
            ))}
          </div>
          <div className="card">
            <h3 className="mb-4">Confusion matrix (test set)</h3>
            <div className="overflow-x-auto">
              <table className="mx-auto border-collapse text-center">
                <thead>
                  <tr>
                    <th className="border border-gray-300 px-4 py-2" />
                    <th className="border border-gray-300 px-4 py-2">Pred 0</th>
                    <th className="border border-gray-300 px-4 py-2">Pred 1</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th className="border border-gray-300 px-4 py-2">Actual 0</th>
                    <td className="border border-gray-300 bg-powder/30 px-6 py-4 text-lg font-bold">{cm[0]?.[0] ?? 0}</td>
                    <td className="border border-gray-300 px-6 py-4">{cm[0]?.[1] ?? 0}</td>
                  </tr>
                  <tr>
                    <th className="border border-gray-300 px-4 py-2">Actual 1</th>
                    <td className="border border-gray-300 px-6 py-4">{cm[1]?.[0] ?? 0}</td>
                    <td className="border border-gray-300 bg-powder/30 px-6 py-4 text-lg font-bold">{cm[1]?.[1] ?? 0}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div className="card">
            <h3 className="mb-3">Workflow statistics</h3>
            <ul className="space-y-1 text-body">
              <li>Total cases: {metrics.workflow_stats.total_cases}</li>
              <li>Pending review: {metrics.workflow_stats.pending_review}</li>
              <li>Approved: {metrics.workflow_stats.approved}</li>
              <li>Rejected: {metrics.workflow_stats.rejected}</li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
