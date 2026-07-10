"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("analytics");
  const [analytics, setAnalytics] = useState<any>(null);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [users, setUsers] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [a, s, u] = await Promise.all([
        api.getAdminAnalytics().catch(() => null),
        api.getSystemHealth().catch(() => null),
        api.getAdminUsers().catch(() => null),
      ]);
      setAnalytics(a);
      setSystemHealth(s);
      setUsers(u);
    } catch { }
    setLoading(false);
  };

  const tabs = [
    { id: "analytics", label: "📊 Analytics" },
    { id: "users", label: "👥 Users" },
    { id: "system", label: "🖥️ System" },
  ];

  if (loading) {
    return (
      <>
        <div className="page-header"><h2>⚙️ Admin Panel</h2></div>
        <div className="page-content">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
            {[1,2,3,4].map(i => <div key={i} className="card skeleton" style={{ height: 100 }} />)}
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="page-header"><h2>⚙️ Admin Panel</h2></div>

      <div className="page-content animate-fade-in">
        {/* Tabs */}
        <div style={{ display: "flex", gap: "0.25rem", marginBottom: "1.25rem", borderBottom: "1px solid var(--border)" }}>
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "0.625rem 1rem", border: "none", cursor: "pointer",
                fontSize: "0.8125rem", fontWeight: activeTab === tab.id ? 600 : 400,
                color: activeTab === tab.id ? "var(--primary)" : "var(--text-secondary)",
                borderBottom: activeTab === tab.id ? "2px solid var(--primary)" : "2px solid transparent",
                background: "transparent",
              }}>{tab.label}</button>
          ))}
        </div>

        {/* Analytics Tab */}
        {activeTab === "analytics" && analytics && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
              <div className="card stat-card">
                <div className="stat-icon" style={{ background: "var(--info-bg)", color: "var(--info)" }}>👥</div>
                <div><div className="stat-value">{analytics.total_users}</div><div className="stat-label">Total Users</div></div>
              </div>
              <div className="card stat-card">
                <div className="stat-icon" style={{ background: "var(--success-bg)", color: "var(--success)" }}>📋</div>
                <div><div className="stat-value">{analytics.total_reports}</div><div className="stat-label">Total Reports</div></div>
              </div>
              <div className="card stat-card">
                <div className="stat-icon" style={{ background: "var(--primary-100)", color: "var(--primary)" }}>💬</div>
                <div><div className="stat-value">{analytics.total_chat_sessions}</div><div className="stat-label">Chat Sessions</div></div>
              </div>
              <div className="card stat-card">
                <div className="stat-icon" style={{ background: "var(--warning-bg)", color: "var(--warning)" }}>✉️</div>
                <div><div className="stat-value">{analytics.total_messages}</div><div className="stat-label">Total Messages</div></div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div className="card">
                <div className="card-header"><h3 style={{ fontSize: "0.9375rem" }}>Users by Role</h3></div>
                <div className="card-body">
                  {Object.entries(analytics.users_by_role || {}).map(([role, count]) => (
                    <div key={role} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--border-light)" }}>
                      <span style={{ textTransform: "capitalize" }}>{role}</span>
                      <span style={{ fontWeight: 600 }}>{String(count)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card">
                <div className="card-header"><h3 style={{ fontSize: "0.9375rem" }}>Reports by Type</h3></div>
                <div className="card-body">
                  {Object.entries(analytics.reports_by_type || {}).map(([type, count]) => (
                    <div key={type} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--border-light)" }}>
                      <span style={{ textTransform: "capitalize" }}>{type.replace("_", " ")}</span>
                      <span style={{ fontWeight: 600 }}>{String(count)}</span>
                    </div>
                  ))}
                  {Object.keys(analytics.reports_by_type || {}).length === 0 && (
                    <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>No reports yet</p>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Users Tab */}
        {activeTab === "users" && users && (
          <div className="card">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.9375rem" }}>Users ({users.total})</h3>
            </div>
            <div className="table-container">
              <table>
                <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th></tr></thead>
                <tbody>
                  {users.users?.map((u: any) => (
                    <tr key={u.id}>
                      <td style={{ fontWeight: 500 }}>{u.full_name}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{u.email}</td>
                      <td><span className={`badge ${u.role === "admin" ? "badge-danger" : u.role === "doctor" ? "badge-info" : "badge-primary"}`}>{u.role}</span></td>
                      <td><span className={`badge ${u.is_active ? "badge-success" : "badge-danger"}`}>{u.is_active ? "Active" : "Inactive"}</span></td>
                      <td style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>{new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* System Tab */}
        {activeTab === "system" && systemHealth && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="card">
              <div className="card-header"><h3 style={{ fontSize: "0.9375rem" }}>System Status</h3></div>
              <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {[
                  { label: "Overall", value: systemHealth.status, ok: systemHealth.status === "healthy" },
                  { label: "Database", value: systemHealth.database, ok: systemHealth.database === "healthy" },
                  { label: "Vector Store", value: systemHealth.vector_store, ok: systemHealth.vector_store === "active" },
                ].map(item => (
                  <div key={item.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.875rem" }}>{item.label}</span>
                    <span className={`badge ${item.ok ? "badge-success" : "badge-danger"}`}>{item.value}</span>
                  </div>
                ))}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.875rem" }}>Uptime</span>
                  <span style={{ fontSize: "0.8125rem", fontWeight: 500 }}>{Math.round((systemHealth.uptime_seconds || 0) / 60)} min</span>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h3 style={{ fontSize: "0.9375rem" }}>ML Models</h3></div>
              <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {Object.entries(systemHealth.ml_models || {}).map(([model, status]) => (
                  <div key={model} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.875rem", textTransform: "capitalize" }}>{model.replace("_", " ")}</span>
                    <span className={`badge ${status === "loaded" ? "badge-success" : "badge-warning"}`}>{String(status)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card" style={{ gridColumn: "1 / -1" }}>
              <div className="card-header"><h3 style={{ fontSize: "0.9375rem" }}>Platform Stats</h3></div>
              <div className="card-body">
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--primary)" }}>{systemHealth.total_users}</div>
                    <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Users</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--secondary)" }}>{systemHealth.total_reports}</div>
                    <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Reports</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent)" }}>{systemHealth.total_chat_sessions}</div>
                    <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Chat Sessions</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Fallback for unauthorized */}
        {!analytics && !loading && (
          <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
            <div style={{ fontSize: "3rem", marginBottom: "0.75rem" }}>🔒</div>
            <h3 style={{ color: "var(--text-secondary)" }}>Admin Access Required</h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
              You need admin privileges to access this panel.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
