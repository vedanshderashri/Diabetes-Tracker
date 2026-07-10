"use client";
import { useState } from "react";
import { api } from "@/lib/api";

export default function DoctorSummaryPage() {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState({ include_reports: true, include_chat_history: true });

  const generateSummary = async () => {
    setLoading(true);
    try {
      const result = await api.generateDoctorSummary(options);
      setSummary(result);
    } catch (err: any) {
      alert(err.message || "Failed to generate summary");
    }
    setLoading(false);
  };

  const exportToPDF = () => {
    if (!summary) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      alert("Please allow popups to export the PDF");
      return;
    }

    const htmlContent = `
      <html>
        <head>
          <title>Clinical Summary - ${summary.patient_name}</title>
          <style>
            body { font-family: 'Outfit', sans-serif; padding: 2rem; color: #1E293B; background: #FFF; }
            h2 { color: #f6833b; border-bottom: 2px solid #FFE5D4; padding-bottom: 0.5rem; margin-top: 0; }
            h3 { color: #863300; margin-top: 1.5rem; border-bottom: 1px solid #E2E8F0; padding-bottom: 0.25rem; font-size: 1.1rem; }
            .section { margin-bottom: 1.5rem; }
            .meta { font-size: 0.875rem; color: #64748B; margin-bottom: 2rem; }
            table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
            th, td { border: 1px solid #E2E8F0; padding: 0.5rem 0.75rem; text-align: left; font-size: 0.875rem; }
            th { background: #FFF3EB; color: #863300; }
            .badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
            .badge-danger { background: #FEE2E2; color: #B91C1C; }
            .badge-warning { background: #FEF3C7; color: #D97706; }
            .badge-primary { background: #FFE5D4; color: #f6833b; }
            .narrative { white-space: pre-wrap; line-height: 1.6; font-size: 0.9rem; background: #F8FAFC; padding: 1rem; border-radius: 6px; }
            .disclaimer { margin-top: 3rem; font-size: 0.75rem; color: #D97706; background: #FFFBEB; padding: 0.75rem; border: 1px solid #FDE68A; border-radius: 6px; }
            @media print {
              body { padding: 0; }
            }
          </style>
        </head>
        <body>
          <h2>Clinical Health Summary</h2>
          <div class="meta">
            <strong>Patient Name:</strong> ${summary.patient_name}<br/>
            <strong>Date Generated:</strong> ${new Date(summary.summary_date).toLocaleString()}
          </div>
          
          ${summary.demographics ? `
            <div class="section">
              <h3>Demographics</h3>
              <table>
                ${Object.entries(summary.demographics).filter(([, val]) => val).map(([key, val]: [string, any]) => `
                  <tr>
                    <td style="width: 30%; font-weight: bold; text-transform: capitalize;">${key.replace("_", " ")}</td>
                    <td>${val}</td>
                  </tr>
                `).join("")}
              </table>
            </div>
          ` : ""}

          ${summary.ai_generated_narrative ? `
            <div class="section">
              <h3>Clinical Narrative</h3>
              <div class="narrative">${summary.ai_generated_narrative}</div>
            </div>
          ` : ""}

          ${summary.chief_complaints?.length > 0 ? `
            <div class="section">
              <h3>Chief Complaints</h3>
              <ul>
                ${summary.chief_complaints.map((c: any) => `<li>${c}</li>`).join("")}
              </ul>
            </div>
          ` : ""}

          ${summary.lab_abnormalities?.length > 0 ? `
            <div class="section">
              <h3>Lab Abnormalities</h3>
              <table>
                <thead>
                  <tr><th>Test</th><th>Value</th><th>Reference Range</th><th>Severity</th></tr>
                </thead>
                <tbody>
                  ${summary.lab_abnormalities.map((l: any) => `
                    <tr>
                      <td style="font-weight: bold;">${l.test}</td>
                      <td>${l.value}</td>
                      <td>${l.reference}</td>
                      <td><span class="badge ${l.is_critical ? "badge-danger" : "badge-warning"}">${l.is_critical ? "Critical" : "Abnormal"}</span></td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          ` : ""}

          ${summary.current_medications?.length > 0 ? `
            <div class="section">
              <h3>Current Medications</h3>
              <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                ${summary.current_medications.map((m: any) => `
                  <span class="badge badge-primary" style="padding: 0.375rem 0.75rem; font-size: 0.8125rem;">
                    ${m.name} ${m.dosage ? `(${m.dosage})` : ""}
                  </span>
                `).join("")}
              </div>
            </div>
          ` : ""}

          ${summary.allergies?.length > 0 ? `
            <div class="section">
              <h3>Allergies</h3>
              <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                ${summary.allergies.map((a: any) => `
                  <span class="badge badge-danger" style="padding: 0.375rem 0.75rem; font-size: 0.8125rem;">${a}</span>
                `).join("")}
              </div>
            </div>
          ` : ""}

          ${summary.recommended_next_steps?.length > 0 ? `
            <div class="section">
              <h3>Recommended Next Steps</h3>
              <ol>
                ${summary.recommended_next_steps.map((s: any) => `<li>${s}</li>`).join("")}
              </ol>
            </div>
          ` : ""}

          <div class="disclaimer">
            ${summary.disclaimer}
          </div>

          <script>
            window.onload = function() {
              window.print();
            }
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
  };

  return (
    <>
      <div className="page-header">
        <h2 style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <svg style={{ width: 20, height: 20, color: "var(--primary)" }} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Doctor Summary
        </h2>
      </div>

      <div className="page-content animate-fade-in">
        {/* Generate Panel */}
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <div className="card-body" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <h3 style={{ fontSize: "1rem", marginBottom: "0.25rem" }}>Generate Clinical Summary</h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                AI-generated summary of your health data for sharing with your doctor
              </p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "0.375rem", fontSize: "0.8125rem", cursor: "pointer" }}>
                <input type="checkbox" checked={options.include_reports} onChange={(e) => setOptions({...options, include_reports: e.target.checked})} />
                Include Reports
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "0.375rem", fontSize: "0.8125rem", cursor: "pointer" }}>
                <input type="checkbox" checked={options.include_chat_history} onChange={(e) => setOptions({...options, include_chat_history: e.target.checked})} />
                Include Chat History
              </label>
              <button className="btn btn-primary" onClick={generateSummary} disabled={loading}>
                {loading ? "Generating..." : "Generate Summary"}
              </button>
            </div>
          </div>
        </div>

        {loading && (
          <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
            <div className="animate-spin" style={{
              width: 40, height: 40, border: "3px solid var(--border)",
              borderTopColor: "var(--primary)", borderRadius: "50%", margin: "0 auto 1rem"
            }} />
            <p style={{ color: "var(--text-secondary)" }}>Analyzing your health data and generating clinical summary...</p>
          </div>
        )}

        {summary && !loading && (
          <div className="card animate-fade-in-up">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ fontSize: "1rem" }}>Clinical Summary — {summary.patient_name}</h3>
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.125rem" }}>
                  Generated: {new Date(summary.summary_date).toLocaleString()}
                </p>
              </div>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn btn-secondary btn-sm" style={{ display: "inline-flex", alignItems: "center", gap: "4px" }} onClick={() => {
                  const text = document.getElementById("summary-content")?.innerText || "";
                  navigator.clipboard.writeText(text);
                }}>
                  <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m-2-3H8" />
                  </svg>
                  Copy
                </button>
                <button className="btn btn-primary btn-sm" style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "white" }} onClick={exportToPDF}>
                  <svg style={{ width: 14, height: 14, color: "white" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download PDF
                </button>
              </div>
            </div>

            <div className="card-body" id="summary-content" style={{ maxHeight: "70vh", overflowY: "auto" }}>
              {/* Demographics */}
              <div style={{ marginBottom: "1.5rem" }}>
                <h4 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                  <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  Demographics
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.5rem" }}>
                  {Object.entries(summary.demographics || {}).filter(([, val]) => val).map(([key, val]: [string, unknown]) => (
                    <div key={key} style={{ fontSize: "0.8125rem" }}>
                      <span style={{ color: "var(--text-muted)" }}>{key.replace("_", " ")}: </span>
                      <span style={{ fontWeight: 500 }}>{String(val)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Narrative */}
              {summary.ai_generated_narrative && (
                <div style={{ marginBottom: "1.5rem" }}>
                  <h4 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Clinical Narrative
                  </h4>
                  <div style={{ padding: "1rem", background: "var(--bg)", borderRadius: "var(--radius-sm)", fontSize: "0.875rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                    {summary.ai_generated_narrative}
                  </div>
                </div>
              )}

              {/* Chief Complaints */}
              {summary.chief_complaints?.length > 0 && (
                <div style={{ marginBottom: "1.5rem" }}>
                  <h4 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    Chief Complaints
                  </h4>
                  <ul style={{ paddingLeft: "1.25rem" }}>
                    {summary.chief_complaints.map((c: string, i: number) => (
                      <li key={i} style={{ fontSize: "0.8125rem", marginBottom: "0.25rem" }}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Lab Abnormalities */}
              {summary.lab_abnormalities?.length > 0 && (
                <div style={{ marginBottom: "1.5rem" }}>
                  <h4 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--warning)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    Lab Abnormalities
                  </h4>
                  <div className="table-container">
                    <table>
                      <thead><tr><th>Test</th><th>Value</th><th>Reference</th><th>Status</th></tr></thead>
                      <tbody>
                        {summary.lab_abnormalities.map((l: any, i: number) => (
                          <tr key={i}>
                            <td style={{ fontWeight: 500 }}>{l.test}</td>
                            <td>{l.value}</td>
                            <td style={{ color: "var(--text-muted)" }}>{l.reference}</td>
                            <td><span className={`badge ${l.is_critical ? "badge-danger" : "badge-warning"}`}>{l.is_critical ? "Critical" : "Abnormal"}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Current Medications */}
              {summary.current_medications?.length > 0 && (
                <div style={{ marginBottom: "1.5rem" }}>
                  <h4 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="5" y="5" width="14" height="14" rx="7" transform="rotate(-45 12 12)" />
                      <line x1="7" y1="17" x2="17" y2="7" />
                    </svg>
                    Current Medications
                  </h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                    {summary.current_medications.map((m: any, i: number) => (
                      <span key={i} className="badge badge-primary" style={{ padding: "0.25rem 0.625rem" }}>
                        {m.name} {m.dosage && `(${m.dosage})`}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Allergies */}
              {summary.allergies?.length > 0 && (
                <div style={{ marginBottom: "1.5rem" }}>
                  <h4 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--danger)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                    Allergies
                  </h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                    {summary.allergies.map((a: string, i: number) => (
                      <span key={i} className="badge badge-danger">{a}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommended Next Steps */}
              {summary.recommended_next_steps?.length > 0 && (
                <div style={{ marginBottom: "1rem" }}>
                  <h4 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                    Recommended Next Steps
                  </h4>
                  <ol style={{ paddingLeft: "1.25rem" }}>
                    {summary.recommended_next_steps.map((s: string, i: number) => (
                      <li key={i} style={{ fontSize: "0.8125rem", marginBottom: "0.375rem" }}>{s}</li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Disclaimer */}
              <div style={{
                marginTop: "1.5rem", padding: "0.75rem", background: "var(--warning-bg)",
                borderRadius: "var(--radius-sm)", fontSize: "0.75rem", color: "#92400E"
              }}>
                {summary.disclaimer}
              </div>
            </div>
          </div>
        )}

        {!summary && !loading && (
          <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
            <div style={{ marginBottom: "1rem" }}>
              <svg style={{ width: 48, height: 48, fill: "var(--primary-light)", margin: "0 auto" }} viewBox="0 0 24 24">
                <path d="M19 10.5h-5.5V5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v5.5H5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5h5.5V19c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-5.5H19c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z" />
              </svg>
            </div>
            <h3 style={{ color: "var(--text-secondary)", marginBottom: "0.5rem" }}>No Summary Generated Yet</h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", maxWidth: 400, margin: "0 auto" }}>
              Click &quot;Generate Summary&quot; to create a comprehensive clinical summary of your health data that you can share with your healthcare provider.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
