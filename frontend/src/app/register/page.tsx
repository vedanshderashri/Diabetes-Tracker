"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", phone: "", language_preference: "en" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.register(form);
      router.push("/chat");
    } catch (err) {
      if (err instanceof ApiError || (err instanceof Error && err.name === 'ApiError')) {
        setError(err.message);
      } else if (err instanceof Error) {
        if (err.message.includes("fetch") || err.message.includes("NetworkError")) {
          setError("Cannot connect to the server. Please ensure the backend is running on port 8000.");
        } else {
          setError(err.message);
        }
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page animate-fade-in">
      <div className="card auth-card">
        <div className="auth-logo">
          <div style={{ display: "inline-block", filter: "drop-shadow(0 4px 6px rgba(59,130,246,0.15))", marginBottom: "0.5rem" }}>
            <svg style={{ width: 48, height: 48, fill: "var(--primary)" }} viewBox="0 0 24 24">
              <path d="M19 10.5h-5.5V5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v5.5H5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5h5.5V19c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-5.5H19c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z" />
            </svg>
          </div>
          <h1>Create Account</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
            Join VitalHealth for intelligent medical diagnostics
          </p>
        </div>

        {error && (
          <div style={{
            padding: "0.75rem 1rem", marginBottom: "1.25rem", borderRadius: "var(--radius)",
            background: "var(--danger-bg)", color: "var(--danger-text)", fontSize: "0.8125rem",
            border: "1px solid rgba(239, 68, 68, 0.15)", display: "flex", gap: "0.5rem", alignItems: "center"
          }}>
            <svg style={{ width: 14, height: 14, flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label className="label" htmlFor="full_name">Full Name</label>
            <input id="full_name" type="text" className="input" placeholder="e.g. John Doe"
              value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required minLength={2} />
          </div>

          <div>
            <label className="label" htmlFor="reg_email">Email Address</label>
            <input id="reg_email" type="email" className="input" placeholder="you@example.com"
              value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              required />
          </div>

          <div>
            <label className="label" htmlFor="reg_password">Password</label>
            <input id="reg_password" type="password" className="input" placeholder="Min 8 characters"
              value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
              required minLength={8} />
          </div>

          <div>
            <label className="label" htmlFor="phone">Phone (optional)</label>
            <input id="phone" type="tel" className="input" placeholder="+91 98765 43210"
              value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>

          <div>
            <label className="label" htmlFor="language">Preferred Language</label>
            <select id="language" className="input"
              value={form.language_preference}
              onChange={(e) => setForm({ ...form, language_preference: e.target.value })}
            >
              <option value="en">English</option>
              <option value="hi">Hindi (हिंदी)</option>
            </select>
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}
            style={{ width: "100%", padding: "0.75rem", display: "flex", gap: "0.5rem", fontWeight: 600, marginTop: "0.5rem" }}>
            {loading ? (
              <>
                <span className="animate-spin" style={{
                  width: 16, height: 16, border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "white", borderRadius: "50%", display: "inline-block"
                }} />
                Creating Account...
              </>
            ) : "Create Account"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: "1.75rem", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
          Already have an account?{" "}
          <Link href="/login" style={{ color: "var(--primary)", fontWeight: 600, textDecoration: "none" }}>Sign In</Link>
        </p>
      </div>
    </div>
  );
}
