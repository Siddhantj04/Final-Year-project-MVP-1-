"use client";

import AuthGuard from "@/components/AuthGuard";
import ErrorAlert from "@/components/ErrorAlert";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ApiError, apiFetch, fetchBlob } from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type CaseDetail = {
  id: number;
  predicted_class: string | null;
  confidence: number | null;
  report_text: string | null;
  image_url: string;
  heatmap_url: string | null;
};

const HEATMAP_NOTICE =
  "The Grad-CAM heatmap is an explanation aid highlighting regions that influenced the model output; it is not a clinical finding.";

export default function ResultsPage() {
  return (
    <AuthGuard>
      <ResultsContent />
    </AuthGuard>
  );
}

function ResultsContent() {
  const params = useParams();
  const caseId = Number(params.id);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [heatmapSrc, setHeatmapSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await apiFetch<CaseDetail>(`/cases/${caseId}`);
        if (cancelled) return;
        setDetail(data);
        const [img, hm] = await Promise.all([
          fetchBlob(data.image_url),
          data.heatmap_url ? fetchBlob(data.heatmap_url) : Promise.resolve(null),
        ]);
        if (!cancelled) {
          setImageSrc(img);
          setHeatmapSrc(hm);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load results.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    if (!Number.isNaN(caseId)) load();
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  const classLabel =
    detail?.predicted_class === "normal_like"
      ? "Normal-like chest X-ray pattern"
      : detail?.predicted_class === "pneumonia_like"
        ? "Possible pneumonia-like pattern"
        : "—";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1>Analysis results</h1>
        <Link href="/dashboard" className="btn-primary text-sm">
          Back to dashboard
        </Link>
      </div>
      <ErrorAlert message={error} />
      {loading && <LoadingSpinner label="Loading case results..." />}
      {!loading && detail && (
        <>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="card">
              <h3 className="mb-3">Original image</h3>
              {imageSrc ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={imageSrc} alt="Original chest X-ray" className="w-full rounded-lg border border-gray-200" />
              ) : (
                <p className="text-body">Image unavailable.</p>
              )}
            </div>
            <div className="card">
              <h3 className="mb-3">Grad-CAM heatmap</h3>
              <p className="mb-3 text-sm text-body">{HEATMAP_NOTICE}</p>
              {heatmapSrc ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={heatmapSrc} alt="Grad-CAM heatmap" className="w-full rounded-lg border border-gray-200" />
              ) : (
                <p className="text-body">Heatmap not available.</p>
              )}
            </div>
          </div>
          <div className="card space-y-2">
            <h3>Model output</h3>
            <p>
              <span className="font-medium text-black">Predicted class:</span> {classLabel}
            </p>
            <p>
              <span className="font-medium text-black">Confidence:</span>{" "}
              {detail.confidence != null ? `${(detail.confidence * 100).toFixed(1)}%` : "—"}
            </p>
          </div>
          <div className="card">
            <h3 className="mb-3">Structured preliminary report</h3>
            <pre className="whitespace-pre-wrap font-sans text-sm text-body">{detail.report_text || "No report."}</pre>
          </div>
        </>
      )}
    </div>
  );
}
