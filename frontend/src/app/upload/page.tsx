"use client";

import AuthGuard from "@/components/AuthGuard";
import ErrorAlert from "@/components/ErrorAlert";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ApiError, apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { ChangeEvent, useMemo, useState } from "react";

const MAX_MB = 10;

function validateClientFile(file: File | null): string[] {
  const messages: string[] = [];
  if (!file) {
    messages.push("Select a JPG or PNG chest X-ray to upload.");
    return messages;
  }
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (!ext || !["jpg", "jpeg", "png"].includes(ext)) {
    messages.push("Only JPG and PNG files are allowed.");
  }
  if (file.size > MAX_MB * 1024 * 1024) {
    messages.push(`File must be ${MAX_MB} MB or smaller.`);
  }
  if (file.size < 1024) {
    messages.push("File appears too small to be a valid image.");
  }
  return messages;
}

export default function UploadPage() {
  return (
    <AuthGuard>
      <UploadContent />
    </AuthGuard>
  );
}

function UploadContent() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [stepLabel, setStepLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const clientErrors = useMemo(() => validateClientFile(file), [file]);
  const canSubmit = file !== null && clientErrors.length === 0 && !loading;

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    setError("");
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(selected ? URL.createObjectURL(selected) : null);
  }

  async function runPipeline() {
    if (!file || clientErrors.length) return;
    setLoading(true);
    setError("");
    try {
      setStepLabel("Uploading image...");
      const form = new FormData();
      form.append("file", file);
      const upload = await apiFetch<{ case_id: number }>("/cases/upload", { method: "POST", body: form });
      const caseId = upload.case_id;

      setStepLabel("Running quality checks...");
      const quality = await apiFetch<{ suitability: string; messages: string[] }>(
        `/cases/${caseId}/quality-check`,
        { method: "POST" },
      );
      if (quality.suitability === "unsuitable") {
        setError(`Image is unsuitable for analysis: ${quality.messages.join(" ")}`);
        setLoading(false);
        setStepLabel("");
        return;
      }

      setStepLabel("Running AI analysis and Grad-CAM...");
      await apiFetch(`/cases/${caseId}/analyze`, { method: "POST" });

      setStepLabel("Generating structured report...");
      await apiFetch(`/cases/${caseId}/report`, { method: "GET" });

      router.push(`/results/${caseId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload pipeline failed.");
    } finally {
      setLoading(false);
      setStepLabel("");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1>Upload chest X-ray</h1>
        <p className="mt-2 text-body">
          JPG or PNG only. Quality checks run before any AI inference. For education and research use only.
        </p>
      </div>
      <div className="card space-y-4">
        <ErrorAlert message={error} />
        {loading && <LoadingSpinner label={stepLabel || "Processing..."} />}
        {!loading && (
          <>
            <div>
              <label className="label-text" htmlFor="xray">
                Select image
              </label>
              <input
                id="xray"
                type="file"
                accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                onChange={onFileChange}
                className="block w-full text-sm text-body"
              />
            </div>
            {clientErrors.length > 0 && file && (
              <ul className="list-disc space-y-1 pl-5 text-sm text-red-600">
                {clientErrors.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            )}
            {file && clientErrors.length === 0 && (
              <p className="text-sm text-green-700">File passed client-side validation.</p>
            )}
            {preview && (
              <div className="overflow-hidden rounded-lg border border-gray-200">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={preview} alt="Upload preview" className="max-h-96 w-full object-contain bg-gray-50" />
              </div>
            )}
            <button type="button" className="btn-primary" disabled={!canSubmit} onClick={runPipeline}>
              Upload and analyze
            </button>
          </>
        )}
      </div>
    </div>
  );
}
