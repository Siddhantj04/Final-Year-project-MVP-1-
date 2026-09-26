"use client";

import AuthGuard from "@/components/AuthGuard";
import ConfirmModal from "@/components/ConfirmModal";
import ErrorAlert from "@/components/ErrorAlert";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ApiError, apiFetch } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

type CaseSummary = {
  id: number;
  status: string;
  quality_status: string | null;
  original_filename: string;
  created_at: string;
  predicted_class: string | null;
  confidence: number | null;
};

type CaseDetail = {
  id: number;
  report_text: string | null;
};

type PendingAction = {
  action: "approve" | "edit" | "reject" | "unsuitable";
  caseId: number;
};

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [editText, setEditText] = useState("");
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function loadCases() {
    setLoading(true);
    setError("");
    try {
      const data = await apiFetch<CaseSummary[]>("/cases");
      setCases(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load cases.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCases();
  }, []);

  async function openCase(id: number) {
    setSelectedId(id);
    setDetailLoading(true);
    setError("");
    try {
      const data = await apiFetch<CaseDetail>(`/cases/${id}`);
      setDetail(data);
      setEditText(data.report_text || "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load case.");
    } finally {
      setDetailLoading(false);
    }
  }

  async function submitDecision() {
    if (!pending) return;
    setSubmitting(true);
    setError("");
    try {
      await apiFetch(`/reviewer/cases/${pending.caseId}/decision`, {
        method: "POST",
        body: JSON.stringify({
          action: pending.action,
          edited_report_text: pending.action === "edit" ? editText : undefined,
        }),
      });
      setPending(null);
      await loadCases();
      if (selectedId === pending.caseId) await openCase(pending.caseId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Review action failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const confirmCopy: Record<string, { title: string; message: string; label: string }> = {
    approve: {
      title: "Approve case",
      message: "Confirm approval of this educational template report?",
      label: "Approve",
    },
    edit: {
      title: "Save edited report",
      message: "Confirm saving your edited report text?",
      label: "Save edit",
    },
    reject: {
      title: "Reject case",
      message: "Confirm rejection of this case?",
      label: "Reject",
    },
    unsuitable: {
      title: "Mark unsuitable",
      message: "Mark this case as unsuitable for the workflow?",
      label: "Mark unsuitable",
    },
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1>Reviewer dashboard</h1>
          <p className="mt-2 text-body">Review cases and record audit-logged decisions.</p>
        </div>
        <Link href="/upload" className="btn-primary">
          New upload
        </Link>
      </div>
      <ErrorAlert message={error} />
      {loading && <LoadingSpinner label="Loading cases..." />}
      {!loading && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="card overflow-x-auto">
            <h3 className="mb-4">All cases</h3>
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-black">
                  <th className="py-2 pr-3">ID</th>
                  <th className="py-2 pr-3">File</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <tr key={c.id} className="border-b border-gray-100">
                    <td className="py-2 pr-3">{c.id}</td>
                    <td className="py-2 pr-3">{c.original_filename}</td>
                    <td className="py-2 pr-3 capitalize">{c.status.replace(/_/g, " ")}</td>
                    <td className="py-2 pr-3">
                      <button type="button" className="text-black underline" onClick={() => openCase(c.id)}>
                        Open
                      </button>{" "}
                      <Link href={`/results/${c.id}`} className="text-black underline">
                        Results
                      </Link>
                    </td>
                  </tr>
                ))}
                {cases.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-4 text-body">
                      No cases yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="card space-y-4">
            <h3>Case review</h3>
            {!selectedId && <p className="text-body">Select a case to review.</p>}
            {selectedId && detailLoading && <LoadingSpinner label="Loading case..." />}
            {selectedId && !detailLoading && detail && (
              <>
                <p className="text-sm text-body">Case #{selectedId}</p>
                <textarea
                  className="input-field min-h-[200px] font-mono text-sm"
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  aria-label="Report text"
                />
                <div className="flex flex-wrap gap-2">
                  {(["approve", "edit", "reject", "unsuitable"] as const).map((action) => (
                    <button
                      key={action}
                      type="button"
                      className="btn-primary capitalize"
                      onClick={() => setPending({ action, caseId: selectedId })}
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {pending && (
        <ConfirmModal
          open
          title={confirmCopy[pending.action].title}
          message={confirmCopy[pending.action].message}
          confirmLabel={confirmCopy[pending.action].label}
          onCancel={() => setPending(null)}
          onConfirm={submitDecision}
          loading={submitting}
        />
      )}
    </div>
  );
}
