"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export default function PredictionPage() {
  const [formData, setFormData] = useState({
    age: 45,
    gender: "Male",
    bmi: 24.5,
    hypertension: false,
    heart_disease: false,
    smoking_history: "never",
    hba1c_level: 5.5,
    blood_glucose_level: 100
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Live Auto-Calculation loop on input modifications
  useEffect(() => {
    const fetchRisk = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.predictDiabetesRisk(formData);
        setResult(response);
      } catch (err: any) {
        setError(err.message || "Failed to calculate risk.");
      }
      setLoading(false);
    };

    const debounceTimer = setTimeout(() => {
      fetchRisk();
    }, 120); // 120ms debounce for extremely responsive fluid needle movement

    return () => clearTimeout(debounceTimer);
  }, [formData]);

  // Needle physics calculations
  const riskScore = result ? result.risk_score : 0.05; // default slight tilt
  const angle = -Math.PI + (riskScore * Math.PI); // Angle from -180deg (left) to 0deg (right)
  const needleLength = 85;
  const needleX = 150 + needleLength * Math.cos(angle);
  const needleY = 130 + needleLength * Math.sin(angle);

  // Status styling based on risk level
  const getRiskStyles = (level: string) => {
    switch (level) {
      case "very_high":
        return { color: "#863300", bg: "rgba(134, 51, 0, 0.1)", label: "Very High Risk" };
      case "high":
        return { color: "#ff6200", bg: "rgba(255, 98, 0, 0.1)", label: "High Risk" };
      case "moderate":
        return { color: "#f6833b", bg: "var(--primary-50)", label: "Moderate Risk" };
      default:
        return { color: "#10B981", bg: "rgba(16, 185, 129, 0.1)", label: "Low Risk" };
    }
  };

  const riskStyles = getRiskStyles(result?.risk_level);

  return (
    <>
      <div className="page-header">
        <h2 style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <svg style={{ width: 20, height: 20, color: "var(--primary)" }} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
          </svg>
          Diabetes Risk Simulator
        </h2>
      </div>

      <div className="page-content animate-fade-in" style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "1.75rem", alignItems: "start" }}>
        
        {/* Left Column: Premium Spaced Form Inputs */}
        <div className="card">
          <div className="card-header" style={{ paddingBottom: "0.25rem" }}>
            <div>
              <h3 style={{ fontSize: "1rem" }}>Adjust Health Indicators</h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>Risk shifts dynamically in real-time as you modify values</p>
            </div>
          </div>
          
          <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "1.5rem", paddingTop: "1rem" }}>
            
            {/* Grid Container for Inputs */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              
              {/* Left Grid Side */}
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {/* Gender selection */}
                <div>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.5rem", display: "block" }}>Gender</label>
                  <select
                    className="input"
                    value={formData.gender}
                    onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                  </select>
                </div>

                {/* Age slider */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                    <label style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Age</label>
                    <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--primary)" }}>{formData.age} yrs</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="100"
                    step="1"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) })}
                    style={{ width: "100%", accentColor: "var(--primary)" }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "2px" }}>
                    <span>Min: 1</span>
                    <span>Max: 100</span>
                  </div>
                </div>

                {/* BMI Slider */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                    <label style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Body Mass Index (BMI)</label>
                    <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--primary)" }}>{formData.bmi.toFixed(1)}</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="60"
                    step="0.1"
                    value={formData.bmi}
                    onChange={(e) => setFormData({ ...formData, bmi: Number(e.target.value) })}
                    style={{ width: "100%", accentColor: "var(--primary)" }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "2px" }}>
                    <span>Min: 10.0</span>
                    <span style={{ fontWeight: 600, color: formData.bmi >= 30 ? "var(--danger)" : formData.bmi >= 25 ? "var(--warning)" : "var(--success)" }}>
                      {formData.bmi < 18.5 ? "Underweight" : formData.bmi < 25 ? "Normal" : formData.bmi < 30 ? "Overweight" : "Obese"}
                    </span>
                    <span>Max: 60.0</span>
                  </div>
                </div>

                {/* Smoking History */}
                <div>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.5rem", display: "block" }}>Smoking History</label>
                  <select
                    className="input"
                    value={formData.smoking_history}
                    onChange={(e) => setFormData({ ...formData, smoking_history: e.target.value })}
                  >
                    <option value="never">Never Smoked</option>
                    <option value="current">Current Smoker</option>
                    <option value="formerly">Former Smoker</option>
                    <option value="not current">Not Current Smoker</option>
                    <option value="ever">Ever Smoked</option>
                    <option value="no info">No Information</option>
                  </select>
                </div>
              </div>

              {/* Right Grid Side */}
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {/* HbA1c Slider */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                    <label style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>HbA1c Level</label>
                    <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--primary)" }}>{formData.hba1c_level.toFixed(1)}%</span>
                  </div>
                  <input
                    type="range"
                    min="3.0"
                    max="15.0"
                    step="0.1"
                    value={formData.hba1c_level}
                    onChange={(e) => setFormData({ ...formData, hba1c_level: Number(e.target.value) })}
                    style={{ width: "100%", accentColor: "var(--primary)" }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "2px" }}>
                    <span>Min: 3.0</span>
                    <span style={{ fontWeight: 600, color: formData.hba1c_level >= 6.5 ? "var(--danger)" : formData.hba1c_level >= 5.7 ? "var(--warning)" : "var(--success)" }}>
                      {formData.hba1c_level < 5.7 ? "Normal" : formData.hba1c_level < 6.5 ? "Pre-diabetic" : "Diabetic"}
                    </span>
                    <span>Max: 15.0</span>
                  </div>
                </div>

                {/* Glucose Slider */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                    <label style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Fasting Blood Glucose</label>
                    <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--primary)" }}>{formData.blood_glucose_level} mg/dL</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="300"
                    step="1"
                    value={formData.blood_glucose_level}
                    onChange={(e) => setFormData({ ...formData, blood_glucose_level: Number(e.target.value) })}
                    style={{ width: "100%", accentColor: "var(--primary)" }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "2px" }}>
                    <span>Min: 50</span>
                    <span style={{ fontWeight: 600, color: formData.blood_glucose_level >= 126 ? "var(--danger)" : formData.blood_glucose_level >= 100 ? "var(--warning)" : "var(--success)" }}>
                      {formData.blood_glucose_level < 100 ? "Normal" : formData.blood_glucose_level < 126 ? "Pre-diabetic" : "Diabetic"}
                    </span>
                    <span>Max: 300</span>
                  </div>
                </div>

                {/* Medical History Switch Buttons */}
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "0.5rem" }}>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)", display: "block" }}>Co-existing Conditions</label>
                  
                  {/* Hypertension Switch */}
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, hypertension: !formData.hypertension })}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      width: "100%",
                      padding: "0.625rem 0.875rem",
                      background: formData.hypertension ? "var(--primary-50)" : "var(--bg)",
                      border: formData.hypertension ? "1px solid var(--primary)" : "1px solid var(--border-dark)",
                      borderRadius: "var(--radius-sm)",
                      color: formData.hypertension ? "var(--primary-hover)" : "var(--text-secondary)",
                      fontWeight: 600,
                      cursor: "pointer",
                      transition: "all 0.15s"
                    }}
                  >
                    <span style={{ fontSize: "0.8125rem" }}>Hypertension</span>
                    <span style={{
                      width: 30,
                      height: 16,
                      backgroundColor: formData.hypertension ? "var(--primary)" : "var(--text-muted)",
                      borderRadius: 8,
                      position: "relative",
                      display: "inline-block",
                      transition: "all 0.15s"
                    }}>
                      <span style={{
                        width: 12,
                        height: 12,
                        backgroundColor: "white",
                        borderRadius: "50%",
                        position: "absolute",
                        top: 2,
                        left: formData.hypertension ? 16 : 2,
                        transition: "all 0.15s"
                      }} />
                    </span>
                  </button>

                  {/* Heart Disease Switch */}
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, heart_disease: !formData.heart_disease })}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      width: "100%",
                      padding: "0.625rem 0.875rem",
                      background: formData.heart_disease ? "var(--primary-50)" : "var(--bg)",
                      border: formData.heart_disease ? "1px solid var(--primary)" : "1px solid var(--border-dark)",
                      borderRadius: "var(--radius-sm)",
                      color: formData.heart_disease ? "var(--primary-hover)" : "var(--text-secondary)",
                      fontWeight: 600,
                      cursor: "pointer",
                      transition: "all 0.15s"
                    }}
                  >
                    <span style={{ fontSize: "0.8125rem" }}>Heart Disease</span>
                    <span style={{
                      width: 30,
                      height: 16,
                      backgroundColor: formData.heart_disease ? "var(--primary)" : "var(--text-muted)",
                      borderRadius: 8,
                      position: "relative",
                      display: "inline-block",
                      transition: "all 0.15s"
                    }}>
                      <span style={{
                        width: 12,
                        height: 12,
                        backgroundColor: "white",
                        borderRadius: "50%",
                        position: "absolute",
                        top: 2,
                        left: formData.heart_disease ? 16 : 2,
                        transition: "all 0.15s"
                      }} />
                    </span>
                  </button>
                </div>
              </div>

            </div>

          </div>
        </div>

        {/* Right Column: Dynamic Speedometer and Analysis */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          
          {/* Speedometer Gauge Card */}
          <div className="card" style={{ padding: "1.75rem", textAlign: "center", position: "relative" }}>
            {loading && (
              <div style={{
                position: "absolute", top: 12, right: 12, display: "flex", alignItems: "center", gap: "4px"
              }}>
                <span className="animate-spin" style={{
                  width: 14, height: 14, borderRadius: "50%",
                  border: "2px solid var(--border-dark)", borderTopColor: "var(--primary)",
                  display: "inline-block"
                }} />
              </div>
            )}
            
            <h3 style={{ fontSize: "1rem", marginBottom: "1rem" }}>Diabetes Risk Index</h3>
            
            <div style={{ width: "100%", maxWidth: 300, margin: "0 auto", position: "relative" }}>
              <svg width="100%" height="150" viewBox="0 0 300 150" style={{ overflow: "visible" }}>
                <defs>
                  <linearGradient id="gauge-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#10B981" />
                    <stop offset="50%" stopColor="#f6833b" />
                    <stop offset="100%" stopColor="#863300" />
                  </linearGradient>
                </defs>
                
                {/* Background track */}
                <path
                  d="M 40 130 A 110 110 0 0 1 260 130"
                  fill="none"
                  stroke="var(--border-dark)"
                  strokeWidth="14"
                  strokeLinecap="round"
                />
                
                {/* Visual score fill */}
                <path
                  d="M 40 130 A 110 110 0 0 1 260 130"
                  fill="none"
                  stroke="url(#gauge-grad)"
                  strokeWidth="14"
                  strokeLinecap="round"
                  strokeDasharray="346"
                  strokeDashoffset={346 - (346 * riskScore)}
                  style={{ transition: "stroke-dashoffset 0.5s ease-out" }}
                />

                {/* Hub */}
                <circle cx="150" cy="130" r="10" fill="var(--text)" />
                <circle cx="150" cy="130" r="5" fill="var(--bg-card)" />
                
                {/* Needle */}
                <line
                  x1="150"
                  y1="130"
                  x2={needleX}
                  y2={needleY}
                  stroke="var(--text)"
                  strokeWidth="4"
                  strokeLinecap="round"
                  style={{ transition: "all 0.5s cubic-bezier(0.18, 0.89, 0.32, 1.15)" }}
                />
              </svg>

              {/* Text label underneath */}
              <div style={{ marginTop: "0.5rem" }}>
                <span style={{ fontSize: "1.875rem", fontWeight: 800, color: result ? riskStyles.color : "var(--text)" }}>
                  {Math.round(riskScore * 100)}%
                </span>
                {result && (
                  <div style={{ marginTop: "0.25rem" }}>
                    <span className="badge" style={{
                      backgroundColor: riskStyles.bg,
                      color: riskStyles.color,
                      fontSize: "0.8125rem",
                      padding: "0.25rem 0.75rem",
                      fontWeight: 700
                    }}>
                      {riskStyles.label}
                    </span>
                  </div>
                )}
              </div>
            </div>
            
            {result?.ml_model_used && (
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "1rem", display: "inline-flex", alignItems: "center", gap: "4px", justifyContent: "center" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10B981" }} />
                scikit-learn Classifier Active
              </div>
            )}
          </div>

          {/* Analysis Card */}
          {result && (
            <div className="card animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
              <div className="card-header" style={{ paddingBottom: "0.5rem" }}>
                <h3 style={{ fontSize: "0.9375rem" }}>Clinical Analysis</h3>
              </div>
              <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "1.25rem", paddingTop: "0.5rem" }}>
                
                {/* Contributing factors */}
                <div>
                  <h4 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text)", marginBottom: "0.375rem" }}>Contributing Parameters</h4>
                  <ul style={{ paddingLeft: "1.15rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                    {result.contributing_factors.map((f: string, i: number) => (
                      <li key={i} style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>{f}</li>
                    ))}
                  </ul>
                </div>

                {/* Recommendations */}
                <div>
                  <h4 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text)", marginBottom: "0.375rem" }}>Suggested Next Steps</h4>
                  <ul style={{ paddingLeft: "1.15rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                    {result.recommendations.map((r: string, i: number) => (
                      <li key={i} style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>{r}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Disclaimer Box */}
          <div style={{
            fontSize: "0.75rem",
            color: "var(--warning-text)",
            background: "var(--warning-bg)",
            padding: "0.75rem",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border)",
            display: "flex",
            gap: "6px",
            alignItems: "flex-start",
            lineHeight: 1.4
          }}>
            <svg style={{ width: 14, height: 14, flexShrink: 0, marginTop: 1 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <strong>Medical Disclaimer:</strong> This simulator provides automated risk assessments based on artificial intelligence classifiers. It is intended for educational purposes only and does NOT constitute a clinical diagnosis or medical prescription.
            </div>
          </div>

        </div>
      </div>
    </>
  );
}
