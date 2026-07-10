"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

function getBezierPoint(
  t: number,
  p0: { x: number; y: number },
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  p3: { x: number; y: number }
) {
  const cx = 3 * (p1.x - p0.x);
  const bx = 3 * (p2.x - p1.x) - cx;
  const ax = p3.x - p0.x - cx - bx;

  const cy = 3 * (p1.y - p0.y);
  const by = 3 * (p2.y - p1.y) - cy;
  const ay = p3.y - p0.y - cy - by;

  const x = ((ax * t + bx) * t + cx) * t + p0.x;
  const y = ((ay * t + by) * t + cy) * t + p0.y;

  return { x, y };
}

const STABILITY_SEGMENTS = [
  { p0: { x: 10, y: 70 }, p1: { x: 50, y: 40 }, p2: { x: 100, y: 80 }, p3: { x: 150, y: 50 } },
  { p0: { x: 150, y: 50 }, p1: { x: 200, y: 20 }, p2: { x: 250, y: 70 }, p3: { x: 300, y: 45 } },
  { p0: { x: 300, y: 45 }, p1: { x: 350, y: 20 }, p2: { x: 400, y: 90 }, p3: { x: 490, y: 60 } }
];

const SEVERITY_SEGMENTS = [
  { p0: { x: 10, y: 95 }, p1: { x: 60, y: 70 }, p2: { x: 110, y: 90 }, p3: { x: 160, y: 55 } },
  { p0: { x: 160, y: 55 }, p1: { x: 210, y: 20 }, p2: { x: 260, y: 85 }, p3: { x: 310, y: 70 } },
  { p0: { x: 310, y: 70 }, p1: { x: 360, y: 55 }, p2: { x: 410, y: 40 }, p3: { x: 490, y: 85 } }
];

const getCurveLookup = () => {
  const stability = [];
  const severity = [];
  const steps = 150;
  for (let seg = 0; seg < 3; seg++) {
    const stabSeg = STABILITY_SEGMENTS[seg];
    const sevSeg = SEVERITY_SEGMENTS[seg];
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      if (seg > 0 && i === 0) continue;
      stability.push(getBezierPoint(t, stabSeg.p0, stabSeg.p1, stabSeg.p2, stabSeg.p3));
      severity.push(getBezierPoint(t, sevSeg.p0, sevSeg.p1, sevSeg.p2, sevSeg.p3));
    }
  }
  return { stability, severity };
};

const { stability: STABILITY_LOOKUP, severity: SEVERITY_LOOKUP } = getCurveLookup();

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [meds, setMeds] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [allergies, setAllergies] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("meds");
  const [hoverX, setHoverX] = useState<number | null>(null);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const svgX = (clientX / rect.width) * 500;
    const clampedX = Math.max(10, Math.min(490, svgX));
    setHoverX(clampedX);
  };

  const handleTouchMove = (e: React.TouchEvent<SVGSVGElement>) => {
    if (e.touches.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.touches[0].clientX - rect.left;
    const svgX = (clientX / rect.width) * 500;
    const clampedX = Math.max(10, Math.min(490, svgX));
    setHoverX(clampedX);
  };

  const hasReports = reports && reports.length > 0;
  const healthScore = data?.health_score?.overall_score ?? 0;
  const effectiveScore = hasReports ? healthScore : 0;

  // Scale factors based on effective health score
  const scaleStab = effectiveScore / 76;
  const scaleSev = 2.0 - 0.01316 * effectiveScore;

  const getScaledPoint = (y: number, isStab: boolean) => {
    const scale = isStab ? scaleStab : scaleSev;
    const scaledY = 110 - (110 - y) * scale;
    return Math.max(10, Math.min(110, scaledY));
  };

  const isHovering = hoverX !== null;
  const activeX = hoverX !== null ? hoverX : 155;

  // Find closest points on both curves
  let closestStab = STABILITY_LOOKUP[0];
  let minStabDiff = Infinity;
  for (let i = 0; i < STABILITY_LOOKUP.length; i++) {
    const diff = Math.abs(STABILITY_LOOKUP[i].x - activeX);
    if (diff < minStabDiff) {
      minStabDiff = diff;
      closestStab = STABILITY_LOOKUP[i];
    }
  }

  let closestSev = SEVERITY_LOOKUP[0];
  let minSevDiff = Infinity;
  for (let i = 0; i < SEVERITY_LOOKUP.length; i++) {
    const diff = Math.abs(SEVERITY_LOOKUP[i].x - activeX);
    if (diff < minSevDiff) {
      minSevDiff = diff;
      closestSev = SEVERITY_LOOKUP[i];
    }
  }

  // Calculate dynamic scaled Y coordinates
  const activeStabY = getScaledPoint(closestStab.y, true);
  const activeSevY = getScaledPoint(closestSev.y, false);

  // Dynamic values
  const stabilityVal = Math.round(76 - (activeStabY - 50) * 0.9);
  const severityVal = Math.round(72 - (activeSevY - 55) * 1.3);

  // Dynamic path strings
  const stabPath = `M 10 ${getScaledPoint(70, true)} ` +
    `C 50 ${getScaledPoint(40, true)}, 100 ${getScaledPoint(80, true)}, 150 ${getScaledPoint(50, true)} ` +
    `C 200 ${getScaledPoint(20, true)}, 250 ${getScaledPoint(70, true)}, 300 ${getScaledPoint(45, true)} ` +
    `C 350 ${getScaledPoint(20, true)}, 400 ${getScaledPoint(90, true)}, 490 ${getScaledPoint(60, true)}`;

  const sevPath = `M 10 ${getScaledPoint(95, false)} ` +
    `C 60 ${getScaledPoint(70, false)}, 110 ${getScaledPoint(90, false)}, 160 ${getScaledPoint(55, false)} ` +
    `C 210 ${getScaledPoint(20, false)}, 260 ${getScaledPoint(85, false)}, 310 ${getScaledPoint(70, false)} ` +
    `C 360 ${getScaledPoint(55, false)}, 410 ${getScaledPoint(40, false)}, 490 ${getScaledPoint(85, false)}`;

  // Time calculations
  const totalMinutes = 10 * 60 + ((activeX - 10) / 480) * 12 * 60;
  let hour = Math.floor(totalMinutes / 60) % 12;
  if (hour === 0) hour = 12;
  const minutes = Math.floor(totalMinutes % 60);
  const ampm = Math.floor(totalMinutes / 60) >= 12 && Math.floor(totalMinutes / 60) < 24 ? "pm" : "am";
  const timeStr = `${hour}:${minutes.toString().padStart(2, '0')}${ampm}`;




  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [dashData, medsData, histData, allergyData, reportsData] = await Promise.all([
        api.getDashboard().catch(() => null),
        api.getMedications().catch(() => []),
        api.getMedicalHistory().catch(() => []),
        api.getAllergies().catch(() => []),
        api.getReports().catch(() => []),
      ]);
      setData(dashData);
      setMeds(medsData);
      setHistory(histData);
      setAllergies(allergyData);
      setReports(reportsData);
    } catch { }
    setLoading(false);
  };

  const handleDeleteItem = async (type: string, id: string) => {
    if (!confirm(`Are you sure you want to delete this ${type}?`)) return;
    try {
      if (type === "report") {
        await api.deleteReport(id);
        setReports(prev => prev.filter(r => r.id !== id));
      } else if (type === "chat") {
        await api.deleteChatSession(id);
        if (data?.recent_chat_sessions) {
          setData({
            ...data,
            recent_chat_sessions: data.recent_chat_sessions.filter((s: any) => s.id !== id)
          });
        }
      } else if (type === "medication") {
        await api.deleteMedication(id);
        setMeds(prev => prev.filter(m => m.id !== id));
      } else if (type === "history") {
        await api.deleteMedicalHistory(id);
        setHistory(prev => prev.filter(h => h.id !== id));
      } else if (type === "allergy") {
        await api.deleteAllergy(id);
        setAllergies(prev => prev.filter(a => a.id !== id));
      }
      const freshDash = await api.getDashboard().catch(() => null);
      if (freshDash) setData(freshDash);
    } catch (err: any) {
      alert(err.message || "Deletion failed");
    }
  };

  if (loading) {
    return (
      <>
        <div className="page-header">
          <h2>Dashboard</h2>
        </div>
        <div className="page-content">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1.25rem" }}>
            {[1, 2, 3, 4].map(i => <div key={i} className="card skeleton" style={{ height: 120 }} />)}
          </div>
        </div>
      </>
    );
  }

  const score = data?.health_score;
  const scoreColor = score?.category === "excellent" ? "var(--success)" :
    score?.category === "good" ? "var(--primary)" :
    score?.category === "fair" ? "var(--warning)" : "var(--danger)";
  const scorePct = `${(score?.overall_score || 0)}%`;

  return (
    <>
      <div className="page-header">
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text)" }}>Dashboard</h2>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>Welcome back! Here is a summary of your health profile.</p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Link href="/chat" className="btn btn-secondary btn-sm" style={{ fontWeight: 600, display: "inline-flex", alignItems: "center" }}>
            <svg style={{ width: 14, height: 14, marginRight: 6 }} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Start Consultation
          </Link>
          <Link href="/reports" className="btn btn-primary btn-sm" style={{ fontWeight: 600, display: "inline-flex", alignItems: "center" }}>
            <svg style={{ width: 14, height: 14, marginRight: 6 }} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Upload Health Report
          </Link>
        </div>
      </div>

      <div className="page-content animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        
        {/* VitalHealth Styled Aligned Stats Cards Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1.25rem" }}>
          
          {/* Card 1: Visitors Style - Overall Health Score */}
          <div className="card stat-card" style={{ display: "flex", flexDirection: "column", alignItems: "stretch", gap: "0.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ background: "var(--primary-50)", color: "var(--primary)", width: 36, height: 36, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg style={{ width: 18, height: 18, color: "var(--primary)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", cursor: "pointer" }}>•••</span>
            </div>
            <div>
              <span className="stat-label" style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Health Score</span>
              <div className="stat-value-row" style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.125rem" }}>
                <span style={{ fontSize: "1.625rem", fontWeight: 700, color: scoreColor }}>{score?.overall_score || 0}</span>
                <span className="stat-trend positive" style={{ fontSize: "0.6875rem", fontWeight: 600, color: scoreColor }}>
                  {score?.category?.replace("_", " ") || "N/A"}
                </span>
              </div>
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.125rem" }}>
              Composite score based on history.
            </p>
          </div>

          {/* Card 2: Doctors Style - AI Chats */}
          <div className="card stat-card" style={{ display: "flex", flexDirection: "column", alignItems: "stretch", gap: "0.5rem", background: "var(--primary-50)", borderColor: "var(--primary-100)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ background: "white", color: "var(--primary)", width: 36, height: 36, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg style={{ width: 18, height: 18, color: "var(--primary)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", cursor: "pointer" }}>•••</span>
            </div>
            <div>
              <span className="stat-label" style={{ fontSize: "0.75rem", color: "var(--primary-hover)" }}>AI Consultations</span>
              <div className="stat-value-row" style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.125rem" }}>
                <span style={{ fontSize: "1.625rem", fontWeight: 700, color: "var(--text)" }}>{data?.recent_chat_sessions?.length || 0}</span>
                <span className="stat-trend positive" style={{ background: "white", color: "var(--primary)", fontSize: "0.6875rem", fontWeight: 600, padding: "0.125rem 0.375rem", borderRadius: "var(--radius-sm)" }}>+15.9%</span>
              </div>
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.125rem", zIndex: 1 }}>
              Active consultations with AI.
            </p>
            {/* Sparkline Graphic Chart */}
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 24, overflow: "hidden", opacity: 0.8 }}>
              <svg width="100%" height="100%" viewBox="0 0 100 20" preserveAspectRatio="none">
                <path d="M0,20 Q10,12 20,15 T40,5 T60,12 T80,3 T100,8 L100,20 Z" fill="rgba(246, 131, 59, 0.05)" stroke="var(--primary)" strokeWidth="1.5" />
              </svg>
            </div>
          </div>

          {/* Card 3: Patient Style - Medical Reports */}
          <div className="card stat-card" style={{ display: "flex", flexDirection: "column", alignItems: "stretch", gap: "0.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ background: "var(--success-bg)", color: "var(--success)", width: 36, height: 36, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg style={{ width: 18, height: 18, color: "var(--success)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", cursor: "pointer" }}>•••</span>
            </div>
            <div>
              <span className="stat-label" style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Reports Analyzed</span>
              <div className="stat-value-row" style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.125rem" }}>
                <span style={{ fontSize: "1.625rem", fontWeight: 700 }}>{reports.length}</span>
                <span className="stat-trend positive" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>Active</span>
              </div>
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.125rem" }}>
              OCR-extracted medical data files.
            </p>
          </div>

          {/* Card 4: Total Bed Style - Clinical Records Breakdown */}
          <div className="card stat-card" style={{ display: "flex", flexDirection: "column", alignItems: "stretch", gap: "0.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ background: "var(--secondary-bg)", color: "var(--secondary)", width: 36, height: 36, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg style={{ width: 18, height: 18, color: "var(--secondary)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
              </div>
              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", cursor: "pointer" }}>•••</span>
            </div>
            <div>
              <span className="stat-label" style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Total Parameters</span>
              <div className="stat-value-row" style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.125rem" }}>
                <span style={{ fontSize: "1.625rem", fontWeight: 700 }}>{meds.length + history.length + allergies.length}</span>
                <span className="stat-trend positive" style={{ fontSize: "0.6875rem", fontWeight: 600 }}>Tracked</span>
              </div>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "0.375rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
              <div>
                <span style={{ fontSize: "0.625rem", color: "var(--text-muted)", display: "block" }}>Medications</span>
                <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>{meds.length} Active</span>
              </div>
              <div>
                <span style={{ fontSize: "0.625rem", color: "var(--text-muted)", display: "block" }}>Conditions</span>
                <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>{history.length} Records</span>
              </div>
            </div>
          </div>

        </div>

        {/* Chart & Calendar Sections */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.25rem" }} className="responsive-grid">
          
          {/* Custom Dual SVG Patient Overview Chart */}
          <div className="card">
            <div className="card-header" style={{ borderBottom: "none", paddingBottom: 0 }}>
              <div>
                <h3 style={{ fontSize: "0.9375rem", fontWeight: 700 }}>Health Overview</h3>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Daily health stability & vitals monitoring timeline</span>
              </div>
              <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", fontWeight: 600 }}>
                <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#f6833b" }} /> Stability Index
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#863300" }} /> Active Severity
                </span>
              </div>
            </div>
            <div className="card-body" style={{ position: "relative", padding: "1.5rem 1rem 1rem 1.5rem" }}>
              <div style={{ width: "100%", height: 200, position: "relative" }}>
                {/* Lock Overlay when no reports have been uploaded yet */}
                {!hasReports && (
                  <div style={{
                    position: "absolute",
                    inset: 0,
                    background: "rgba(255, 255, 255, 0.4)",
                    backdropFilter: "blur(4px)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "var(--radius-lg)",
                    zIndex: 20,
                    textAlign: "center",
                    padding: "1.5rem"
                  }} className="dark:bg-slate-900/60">
                    <div style={{
                      background: "var(--primary-50)",
                      color: "var(--primary)",
                      padding: "0.75rem",
                      borderRadius: "50%",
                      marginBottom: "0.75rem"
                    }}>
                      <svg style={{ width: 24, height: 24 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h4 style={{ fontWeight: 700, fontSize: "0.9375rem", color: "var(--text)" }}>Vitals Timeline Locked</h4>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", maxWidth: "260px", marginTop: "4px" }}>
                      Please upload your first health report to activate dynamic stability index and active severity tracking.
                    </p>
                    <Link href="/reports" className="btn btn-primary btn-sm" style={{ marginTop: "1rem", fontSize: "0.75rem", padding: "0.5rem 1rem" }}>
                      Upload Report
                    </Link>
                  </div>
                )}

                <svg
                  width="100%"
                  height="100%"
                  viewBox="0 0 500 120"
                  preserveAspectRatio="none"
                  onMouseMove={handleMouseMove}
                  onMouseLeave={() => setHoverX(null)}
                  onTouchMove={handleTouchMove}
                  onTouchEnd={() => setHoverX(null)}
                  style={{ cursor: "crosshair", overflow: "visible" }}
                >
                  {[0, 25, 50, 75, 100].map(y => (
                    <line key={y} x1="0" y1={y} x2="500" y2={y} stroke="var(--border)" strokeWidth="0.5" />
                  ))}
                  
                  <path
                    d={stabPath}
                    fill="none"
                    stroke="#f6833b"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  
                  <path
                    d={sevPath}
                    fill="none"
                    stroke="#863300"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeDasharray="1 1"
                  />

                  {/* Tracking vertical guide line - only visible when hovering */}
                  {isHovering && (
                    <line
                      x1={activeX}
                      y1={10}
                      x2={activeX}
                      y2={110}
                      stroke="var(--border-dark)"
                      strokeWidth="1.5"
                      strokeDasharray="3 3"
                    />
                  )}

                  {/* Interactive markers on paths */}
                  <circle
                    cx={isHovering ? closestStab.x : 150}
                    cy={isHovering ? activeStabY : getScaledPoint(50, true)}
                    r="5"
                    fill="#f6833b"
                    stroke="var(--bg-card)"
                    strokeWidth="1.5"
                    style={{ transition: isHovering ? "none" : "cx 0.2s ease, cy 0.2s ease" }}
                  />
                  <circle
                    cx={isHovering ? closestSev.x : 160}
                    cy={isHovering ? activeSevY : getScaledPoint(55, false)}
                    r="5"
                    fill="#863300"
                    stroke="var(--bg-card)"
                    strokeWidth="1.5"
                    style={{ transition: isHovering ? "none" : "cx 0.2s ease, cy 0.2s ease" }}
                  />
                </svg>

                {/* Floating rich dynamic tooltip details */}
                <div style={{
                  position: "absolute",
                  top: isHovering ? `${activeStabY - 32}px` : `${getScaledPoint(50, true) - 32}px`,
                  left: isHovering ? `${(activeX / 500) * 100}%` : `${(150 / 500) * 100}%`,
                  transform: "translateX(-50%)",
                  background: "#0b0f19",
                  color: "white",
                  padding: "0.25rem 0.625rem",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.6875rem",
                  fontWeight: 600,
                  boxShadow: "var(--shadow-md)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  pointerEvents: "none",
                  whiteSpace: "nowrap",
                  zIndex: 10,
                  transition: isHovering ? "none" : "left 0.2s ease, top 0.2s ease",
                  border: "1px solid rgba(255,255,255,0.05)"
                }}>
                  <svg style={{ width: 12, height: 12, fill: "none", stroke: "currentColor", strokeWidth: 2.5 }} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                  Stable Index {isHovering ? stabilityVal : Math.max(0, Math.round(76 - (getScaledPoint(50, true) - 50) * 0.9))}%
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "0.5rem", padding: "0 0.5rem" }}>
                <span>10am</span><span>12pm</span><span>02pm</span><span>04pm</span><span>06pm</span><span>08pm</span><span>10pm</span>
              </div>
            </div>
          </div>

          {/* Custom Calendar Widget Card */}
          <div className="card calendar-widget">
            <div className="calendar-header">
              <span style={{ fontSize: "0.875rem", fontWeight: 700 }}>July 2026</span>
              <div style={{ display: "flex", gap: "0.25rem" }}>
                <button className="btn btn-ghost" style={{ padding: "0.125rem 0.25rem", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                  <svg style={{ width: 12, height: 12 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
                </button>
                <button className="btn btn-ghost" style={{ padding: "0.125rem 0.25rem", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                  <svg style={{ width: 12, height: 12 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
                </button>
              </div>
            </div>
            <div className="calendar-grid">
              {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
                <span key={i} className="calendar-day-label">{d}</span>
              ))}
              
              {Array.from({ length: 31 }, (_, i) => {
                const day = i + 1;
                const active = day === 11;
                return (
                  <div key={day} className={`calendar-day ${active ? "active" : ""}`}>
                    <span>{day}</span>
                    <div className="calendar-dots">
                      {day % 7 === 1 && <span className="dot dot-appointment" />}
                      {day % 10 === 0 && <span className="dot dot-meeting" />}
                      {day % 12 === 3 && <span className="dot dot-surgery" />}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>

        {/* Dynamic Personal Health Records Table */}
        <div className="card" style={{ marginTop: "0.25rem" }}>
          <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "none", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Personal Health Records</h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>View, manage, and inspect your medication, history, and medical records</p>
            </div>
            
            {/* Filter Tabs */}
            <div className="tab-nav" style={{ flexShrink: 0 }}>
              <button onClick={() => setActiveTab("meds")} className={`tab-btn ${activeTab === "meds" ? "active" : ""}`}>Medications</button>
              <button onClick={() => setActiveTab("history")} className={`tab-btn ${activeTab === "history" ? "active" : ""}`}>Medical History</button>
              <button onClick={() => setActiveTab("allergies")} className={`tab-btn ${activeTab === "allergies" ? "active" : ""}`}>Allergies</button>
              <button onClick={() => setActiveTab("reports")} className={`tab-btn ${activeTab === "reports" ? "active" : ""}`}>Reports</button>
            </div>
          </div>

          <div className="table-container" style={{ padding: "0 1.5rem 1.5rem" }}>
            {activeTab === "meds" && (
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 40 }}><div className="checkbox-container"><input type="checkbox" readOnly /></div></th>
                    <th>Medication Name</th>
                    <th>Dosage</th>
                    <th>Frequency</th>
                    <th>Status</th>
                    <th style={{ width: 50 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {meds.length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>No medications tracked</td></tr>
                  ) : (
                    meds.map((m, idx) => (
                      <tr key={m.id}>
                        <td><div className="checkbox-container"><input type="checkbox" readOnly /></div></td>
                        <td className="patient-cell">
                          <div className="patient-cell-avatar" style={{ background: "var(--success-bg)", color: "var(--success)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <svg style={{ width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="5" y="5" width="14" height="14" rx="7" transform="rotate(-45 12 12)" />
                              <line x1="7" y1="17" x2="17" y2="7" />
                            </svg>
                          </div>
                          <div className="patient-cell-details">
                            <span className="patient-cell-name">{m.name}</span>
                            <span className="patient-cell-sub">Daily Prescription</span>
                          </div>
                        </td>
                        <td>{m.dosage || "—"}</td>
                        <td>{m.frequency || "—"}</td>
                        <td>
                          <span className={`badge ${m.is_active ? "badge-success" : "badge-info"}`}>
                            {m.is_active ? "Active" : "Ended"}
                          </span>
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <button
                            onClick={() => handleDeleteItem("medication", m.id)}
                            className="btn btn-ghost btn-sm"
                            style={{ color: "var(--danger)", padding: "0.25rem 0.5rem", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
                            title="Delete Medication"
                          >
                            <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}

            {activeTab === "history" && (
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 40 }}><div className="checkbox-container"><input type="checkbox" readOnly /></div></th>
                    <th>Condition</th>
                    <th>Status</th>
                    <th>Diagnosed</th>
                    <th>Notes</th>
                    <th style={{ width: 50 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {history.length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>No medical history recorded</td></tr>
                  ) : (
                    history.map((h, idx) => (
                      <tr key={h.id}>
                        <td><div className="checkbox-container"><input type="checkbox" readOnly /></div></td>
                        <td className="patient-cell">
                          <div className="patient-cell-avatar" style={{ background: "var(--warning-bg)", color: "var(--warning)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <svg style={{ width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                            </svg>
                          </div>
                          <div className="patient-cell-details">
                            <span className="patient-cell-name">{h.condition}</span>
                            <span className="patient-cell-sub">Condition diagnosis</span>
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${h.status === "active" ? "badge-warning" : h.status === "resolved" ? "badge-success" : "badge-info"}`}>
                            {h.status}
                          </span>
                        </td>
                        <td style={{ color: "var(--text-secondary)" }}>
                          {h.diagnosed_date ? new Date(h.diagnosed_date).toLocaleDateString() : "—"}
                        </td>
                        <td style={{ color: "var(--text-secondary)" }}>{h.notes || "—"}</td>
                        <td style={{ textAlign: "center" }}>
                          <button
                            onClick={() => handleDeleteItem("history", h.id)}
                            className="btn btn-ghost btn-sm"
                            style={{ color: "var(--danger)", padding: "0.25rem 0.5rem", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
                            title="Delete Medical History"
                          >
                            <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}

            {activeTab === "allergies" && (
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 40 }}><div className="checkbox-container"><input type="checkbox" readOnly /></div></th>
                    <th>Allergen</th>
                    <th>Severity</th>
                    <th>Reaction</th>
                    <th style={{ width: 50 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {allergies.length === 0 ? (
                    <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)" }}>No allergies recorded</td></tr>
                  ) : (
                    allergies.map((a, idx) => (
                      <tr key={a.id}>
                        <td><div className="checkbox-container"><input type="checkbox" readOnly /></div></td>
                        <td className="patient-cell">
                          <div className="patient-cell-avatar" style={{ background: "var(--danger-bg)", color: "var(--danger)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <svg style={{ width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                          </div>
                          <div className="patient-cell-details">
                            <span className="patient-cell-name">{a.allergen}</span>
                            <span className="patient-cell-sub">Allergic reactant</span>
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${a.severity === "severe" ? "badge-danger" : a.severity === "moderate" ? "badge-warning" : "badge-info"}`}>
                            {a.severity}
                          </span>
                        </td>
                        <td style={{ color: "var(--text-secondary)" }}>{a.reaction || "—"}</td>
                        <td style={{ textAlign: "center" }}>
                          <button
                            onClick={() => handleDeleteItem("allergy", a.id)}
                            className="btn btn-ghost btn-sm"
                            style={{ color: "var(--danger)", padding: "0.25rem 0.5rem", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
                            title="Delete Allergy"
                          >
                            <svg style={{ width: 14, height: 14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}

            {activeTab === "reports" && (
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 40 }}><div className="checkbox-container"><input type="checkbox" readOnly /></div></th>
                    <th>File Name</th>
                    <th>Report Type</th>
                    <th>Upload Date</th>
                    <th>Status</th>
                    <th style={{ width: 50 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {reports.length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>No reports uploaded</td></tr>
                  ) : (
                    reports.map(r => (
                      <tr key={r.id}>
                        <td><div className="checkbox-container"><input type="checkbox" readOnly /></div></td>
                        <td className="patient-cell">
                          <div className="patient-cell-avatar" style={{ background: "var(--info-bg)", color: "var(--info)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <svg style={{ width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </div>
                          <div className="patient-cell-details">
                            <span className="patient-cell-name" style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.file_name}</span>
                            <span className="patient-cell-sub">{r.file_type.toUpperCase()} File</span>
                          </div>
                        </td>
                        <td>
                          <span className="badge badge-info" style={{ textTransform: "capitalize" }}>
                            {r.report_type?.replace("_", " ") || r.file_type}
                          </span>
                        </td>
                        <td style={{ color: "var(--text-secondary)" }}>{new Date(r.upload_date).toLocaleDateString()}</td>
                        <td>
                          <span className={`badge ${r.status === "analyzed" ? "badge-success" : r.status === "error" ? "badge-danger" : "badge-warning"}`}>
                            {r.status}
                          </span>
                        </td>
                        <td>
                          <button
                            onClick={() => handleDeleteItem("report", r.id)}
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
                    ))
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Dynamic Insights / Recommendations Section */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: "1.25rem" }} className="responsive-grid">
          
          {/* Risk Alerts */}
          <div className="card">
            <div className="card-header" style={{ display: "flex", gap: "6px", alignItems: "center", justifyContent: "flex-start" }}>
              <svg style={{ width: 16, height: 16, color: "var(--danger)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 700 }}>Critical Warnings</h3>
            </div>
            <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {data?.risk_indicators?.length > 0 ? (
                data.risk_indicators.map((ri: any, i: number) => (
                  <div key={i} className={`badge ${ri.level === "high" ? "badge-danger" : "badge-warning"}`}
                    style={{ padding: "0.625rem 0.875rem", justifyContent: "flex-start", width: "100%", borderRadius: "var(--radius)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                    {ri.message}
                  </div>
                ))
              ) : (
                <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", display: "flex", alignItems: "center" }}>
                  <svg style={{ width: 14, height: 14, color: "var(--success)", marginRight: 8, flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  No clinical risk indicators detected at this time.
                </p>
              )}
            </div>
          </div>
 
          {/* AI Insights & Recommendations */}
          <div className="card">
            <div className="card-header" style={{ display: "flex", gap: "6px", alignItems: "center", justifyContent: "flex-start" }}>
              <svg style={{ width: 16, height: 16, color: "var(--warning)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 700 }}>Health Insights & AI Recommendations</h3>
            </div>
            <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {data?.health_insights?.length > 0 ? (
                data.health_insights.map((insight: string, i: number) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
                    <svg style={{ width: 14, height: 14, color: "var(--primary)", marginTop: 3, flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                    </svg>
                    <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                      {insight}
                    </span>
                  </div>
                ))
              ) : (
                <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                  Upload comprehensive reports or describe symptom logs to generate medical suggestions.
                </p>
              )}
            </div>
          </div>

        </div>

      </div>

      <style>{`
        @media (max-width: 1024px) {
          .responsive-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </>
  );
}
