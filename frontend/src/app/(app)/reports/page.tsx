"use client";
import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [selectedReport, setSelectedReport] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dragover, setDragover] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const r = await api.getReports();
      setReports(r);
    } catch { }
    setLoading(false);
  };

  const handleUpload = async (file: File) => {
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "jpg", "jpeg", "png"].includes(ext || "")) {
      alert("Only PDF, JPG, and PNG files are allowed");
      return;
    }
    setUploading(true);
    try {
      const report = await api.uploadReport(file);
      setReports(prev => [report, ...prev]);
      setSelectedReport(null);
      // Reload to get full analysis
      setTimeout(async () => {
        try {
          const detail = await api.getReport(report.id);
          setSelectedReport(detail);
          setReports(prev => prev.map(r => r.id === report.id ? { ...r, ...detail } : r));
        } catch { }
      }, 1000);
    } catch (err: any) {
      alert(err.message || "Upload failed");
    }
    setUploading(false);
  };

  const viewReport = async (reportId: string) => {
    try {
      const detail = await api.getReport(reportId);
      setSelectedReport(detail);
    } catch { }
  };

  const handleDeleteReport = async (reportId: string) => {
    if (!confirm("Are you sure you want to delete this report? This will also remove any parsed lab values.")) return;
    try {
      await api.deleteReport(reportId);
      setReports(prev => prev.filter(r => r.id !== reportId));
      if (selectedReport?.id === reportId) {
        setSelectedReport(null);
      }
    } catch (err: any) {
      alert(err.message || "Failed to delete report");
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Medical Reports</h2>
      </div>

      <div className="page-content animate-fade-in">
        {/* Upload Zone */}
        <div
          className={`upload-zone ${dragover ? "dragover" : ""}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
          onDragLeave={() => setDragover(false)}
          onDrop={(e) => {
            e.preventDefault(); setDragover(false);
            const file = e.dataTransfer.files[0];
            if (file) handleUpload(file);
          }}
          style={{ marginBottom: "1.5rem" }}
        >
          <input ref={fileInputRef} type="file" accept=".pdf,.jpg,.jpeg,.png" style={{ display: "none" }}
            onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }} />
          {uploading ? (
            <div>
              <div className="animate-spin" style={{
                width: 32, height: 32, border: "3px solid var(--border)",
                borderTopColor: "var(--primary)", borderRadius: "50%", margin: "0 auto 0.75rem"
              }} />
              <p style={{ color: "var(--primary)", fontWeight: 500 }}>Analyzing report...</p>
            </div>
          ) : (
            <>
              <svg style={{ width: 32, height: 32, margin: "0 auto 0.75rem", color: "var(--text-secondary)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              <p style={{ fontWeight: 500, marginBottom: "0.25rem" }}>
                Drop a medical report here or click to upload
              </p>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                Supports PDF, JPG, PNG — Max 20MB
              </p>
            </>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: selectedReport ? "1fr 1fr" : "1fr", gap: "1rem" }}>
          {/* Report List */}
          <div className="card">
            <div className="card-header"><h3 style={{ fontSize: "0.9375rem" }}>Your Reports</h3></div>
            {loading ? (
              <div className="card-body">
                {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 48, marginBottom: "0.5rem" }} />)}
              </div>
            ) : reports.length === 0 ? (
              <div className="card-body" style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                No reports uploaded yet
              </div>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr><th>File</th><th>Type</th><th>Status</th><th>Date</th><th style={{ width: 50 }}></th></tr>
                  </thead>
                  <tbody>
                    {reports.map(r => (
                      <tr key={r.id} onClick={() => viewReport(r.id)} style={{ cursor: "pointer" }}>
                        <td style={{ fontWeight: 500, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {r.file_name}
                        </td>
                        <td><span className="badge badge-info">{r.report_type || r.file_type}</span></td>
                        <td>
                          <span className={`badge ${r.status === "analyzed" ? "badge-success" : r.status === "error" ? "badge-danger" : "badge-warning"}`}>
                            {r.status}
                          </span>
                        </td>
                        <td style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                          {new Date(r.upload_date).toLocaleDateString()}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteReport(r.id);
                            }}
                            className="btn btn-ghost btn-sm"
                            style={{ color: "var(--danger)", padding: "0.25rem 0.5rem", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
                            title="Delete Report"
                          >
                            <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Report Detail */}
          {selectedReport && (
            <div className="card animate-fade-in">
              <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ fontSize: "0.9375rem", display: "flex", alignItems: "center", gap: "6px" }}>
                  <svg style={{ width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Report Analysis
                </h3>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ color: "var(--danger)", display: "inline-flex", alignItems: "center", gap: "4px" }}
                    onClick={() => handleDeleteReport(selectedReport.id)}
                    title="Delete Report"
                  >
                    <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Delete
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setSelectedReport(null)}>✕</button>
                </div>
              </div>
              <div className="card-body" style={{ maxHeight: "60vh", overflowY: "auto" }}>
                <div style={{ marginBottom: "1rem" }}>
                  <div className="label">Report Type</div>
                  <span className="badge badge-primary" style={{ textTransform: "capitalize" }}>
                    {selectedReport.report_type?.replace("_", " ") || "Unknown"}
                  </span>
                </div>

                {selectedReport.ai_summary && (
                  <div style={{ marginBottom: "1rem" }}>
                    <div className="label">AI Summary</div>
                    <p style={{ fontSize: "0.875rem", lineHeight: 1.6 }}>{selectedReport.ai_summary}</p>
                  </div>
                )}

                {selectedReport.ai_explanation && (
                  <div style={{ marginBottom: "1rem" }}>
                    <div className="label">Simple Explanation</div>
                    <div style={{
                      padding: "0.75rem", background: "var(--info-bg)",
                      borderRadius: "var(--radius-sm)", fontSize: "0.875rem", lineHeight: 1.6
                    }}>
                      {selectedReport.ai_explanation}
                    </div>
                  </div>
                )}

                {selectedReport.critical_findings && (
                  <div className="emergency-banner" style={{ marginBottom: "1rem", display: "flex", gap: "8px", alignItems: "flex-start" }}>
                    <svg style={{ width: 20, height: 20, color: "var(--danger)", flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: "0.25rem", color: "var(--danger)" }}>Critical Findings</div>
                      <p style={{ fontSize: "0.875rem" }}>{selectedReport.critical_findings}</p>
                    </div>
                  </div>
                )}

                {selectedReport.lab_values?.length > 0 && (
                  <div>
                    <div className="label" style={{ marginBottom: "0.5rem" }}>Lab Values</div>
                    <div className="table-container">
                      <table>
                        <thead>
                          <tr><th>Test</th><th>Value</th><th>Reference</th><th>Status</th></tr>
                        </thead>
                        <tbody>
                          {selectedReport.lab_values.map((lv: any) => (
                            <tr key={lv.id}>
                              <td style={{ fontWeight: 500 }}>{lv.test_name}</td>
                              <td>{lv.value} {lv.unit}</td>
                              <td style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                                {lv.reference_range_low != null ? `${lv.reference_range_low}–${lv.reference_range_high}` : "—"}
                              </td>
                              <td>
                                {lv.is_critical ? (
                                  <span className="badge badge-danger">Critical</span>
                                ) : lv.is_abnormal ? (
                                  <span className="badge badge-warning">Abnormal</span>
                                ) : (
                                  <span className="badge badge-success">Normal</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
