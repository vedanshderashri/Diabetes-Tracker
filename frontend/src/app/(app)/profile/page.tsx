"use client";
import { useEffect, useState, FormEvent } from "react";
import { api } from "@/lib/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [medications, setMedications] = useState<any[]>([]);
  const [allergies, setAllergies] = useState<any[]>([]);
  const [account, setAccount] = useState<any>(null);
  const [activeTab, setActiveTab] = useState("profile");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingAccount, setSavingAccount] = useState(false);
  const [form, setForm] = useState<any>({});
  const [accountForm, setAccountForm] = useState<any>({});
  const [showAddModal, setShowAddModal] = useState<string | null>(null);
  const [addForm, setAddForm] = useState<any>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [p, h, m, a, acc] = await Promise.all([
        api.getProfile().catch(() => null),
        api.getMedicalHistory().catch(() => []),
        api.getMedications().catch(() => []),
        api.getAllergies().catch(() => []),
        api.getMe().catch(() => null),
      ]);
      setProfile(p);
      setForm(p || {});
      setHistory(h);
      setMedications(m);
      setAllergies(a);
      setAccount(acc);
      setAccountForm(acc ? {
        full_name: acc.full_name,
        phone: acc.phone || "",
        language_preference: acc.language_preference,
        password: ""
      } : {});
    } catch { }
    setLoading(false);
  };

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await api.updateProfile(form);
      setProfile(updated);
      alert("Profile details saved successfully");
    } catch (err: any) {
      alert(err.message || "Failed to save profile");
    }
    setSaving(false);
  };

  const saveAccount = async (e: FormEvent) => {
    e.preventDefault();
    setSavingAccount(true);
    try {
      const data: any = {
        full_name: accountForm.full_name,
        phone: accountForm.phone || null,
        language_preference: accountForm.language_preference,
      };
      if (accountForm.password) {
        data.password = accountForm.password;
      }
      const updated = await api.updateAccount(data);
      setAccount(updated);
      const localUser = api.getUser();
      if (localUser) {
        api.setUser({ ...localUser, ...updated });
      }
      alert("Account details updated successfully");
      setAccountForm((prev: any) => ({ ...prev, password: "" }));
    } catch (err: any) {
      alert(err.message || "Failed to update account");
    }
    setSavingAccount(false);
  };

  const handleClearChats = async () => {
    if (!confirm("Are you sure you want to permanently delete all chat conversations and messages? This cannot be undone.")) return;
    try {
      await api.clearAllChatSessions();
      alert("All chat conversations have been cleared.");
    } catch (err: any) {
      alert(err.message || "Failed to clear chats");
    }
  };

  const handleClearReports = async () => {
    if (!confirm("Are you sure you want to permanently delete all uploaded reports and parsed lab results? This cannot be undone.")) return;
    try {
      await api.clearAllReports();
      alert("All uploaded reports have been cleared.");
    } catch (err: any) {
      alert(err.message || "Failed to clear reports");
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm("CRITICAL WARNING: Are you sure you want to permanently delete your account and all associated health records, chats, and uploaded files? This action is irreversible.")) return;
    try {
      await api.deleteAccount();
      alert("Your account and all associated data have been permanently deleted.");
      api.logout();
    } catch (err: any) {
      alert(err.message || "Failed to delete account");
    }
  };

  const addItem = async () => {
    if (!showAddModal) return;
    try {
      if (showAddModal === "history") {
        const item = await api.addMedicalHistory(addForm);
        setHistory(prev => [...prev, item]);
      } else if (showAddModal === "medication") {
        const item = await api.addMedication(addForm);
        setMedications(prev => [...prev, item]);
      } else if (showAddModal === "allergy") {
        const item = await api.addAllergy(addForm);
        setAllergies(prev => [...prev, item]);
      }
      setShowAddModal(null);
      setAddForm({});
    } catch (err: any) { alert(err.message); }
  };

  const handleDeleteItem = async (type: string, id: string) => {
    if (!confirm(`Are you sure you want to delete this ${type}?`)) return;
    try {
      if (type === "medication") {
        await api.deleteMedication(id);
        setMedications(prev => prev.filter(m => m.id !== id));
      } else if (type === "history") {
        await api.deleteMedicalHistory(id);
        setHistory(prev => prev.filter(h => h.id !== id));
      } else if (type === "allergy") {
        await api.deleteAllergy(id);
        setAllergies(prev => prev.filter(a => a.id !== id));
      }
    } catch (err: any) {
      alert(err.message || "Deletion failed");
    }
  };

  const tabs = [
    { id: "profile", label: "Profile", icon: (
      <svg style={{ width: 14, height: 14, marginRight: 6 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ) },
    { id: "history", label: "Medical History", icon: (
      <svg style={{ width: 14, height: 14, marginRight: 6 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ) },
    { id: "medications", label: "Medications", icon: (
      <svg style={{ width: 14, height: 14, marginRight: 6 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="5" y="5" width="14" height="14" rx="7" transform="rotate(-45 12 12)" />
        <line x1="7" y1="17" x2="17" y2="7" />
      </svg>
    ) },
    { id: "allergies", label: "Allergies", icon: (
      <svg style={{ width: 14, height: 14, marginRight: 6 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ) },
  ];

  if (loading) {
    return (
      <>
        <div className="page-header"><h2>Health Profile</h2></div>
        <div className="page-content"><div className="card skeleton" style={{ height: 400 }} /></div>
      </>
    );
  }

  return (
    <>
      <div className="page-header"><h2>Health Profile</h2></div>

      <div className="page-content animate-fade-in">
        {/* Tabs */}
        <div style={{ display: "flex", gap: "0.25rem", marginBottom: "1rem", borderBottom: "1px solid var(--border)", paddingBottom: "0" }}>
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "0.625rem 1rem", border: "none", cursor: "pointer",
                fontSize: "0.8125rem", fontWeight: activeTab === tab.id ? 600 : 400,
                color: activeTab === tab.id ? "var(--primary)" : "var(--text-secondary)",
                borderBottom: activeTab === tab.id ? "2px solid var(--primary)" : "2px solid transparent",
                background: "transparent", transition: "all 0.15s",
                display: "inline-flex",
                alignItems: "center"
              }}>{tab.icon}{tab.label}</button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === "profile" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              {/* Clinical Profile Details */}
              <div className="card">
                <div className="card-header">
                  <h3 style={{ fontSize: "0.9375rem" }}>Health & Clinical Profile</h3>
                </div>
                <div className="card-body">
                  <form onSubmit={saveProfile}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                      <div>
                        <label className="label">Date of Birth</label>
                        <input type="date" className="input" value={form.date_of_birth || ""}
                          onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} />
                      </div>
                      <div>
                        <label className="label">Gender</label>
                        <select className="input" value={form.gender || ""}
                          onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                          <option value="">Select...</option>
                          <option value="male">Male</option>
                          <option value="female">Female</option>
                          <option value="other">Other</option>
                        </select>
                      </div>
                      <div>
                        <label className="label">Blood Type</label>
                        <select className="input" value={form.blood_type || ""}
                          onChange={(e) => setForm({ ...form, blood_type: e.target.value })}>
                          <option value="">Select...</option>
                          {["A+","A-","B+","B-","AB+","AB-","O+","O-"].map(bt => <option key={bt} value={bt}>{bt}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="label">Height (cm)</label>
                        <input type="number" className="input" value={form.height_cm || ""}
                          onChange={(e) => setForm({ ...form, height_cm: parseFloat(e.target.value) || null })} />
                      </div>
                      <div>
                        <label className="label">Weight (kg)</label>
                        <input type="number" className="input" value={form.weight_kg || ""}
                          onChange={(e) => setForm({ ...form, weight_kg: parseFloat(e.target.value) || null })} />
                      </div>
                      <div>
                        <label className="label">Emergency Contact</label>
                        <input type="text" className="input" value={form.emergency_contact_name || ""}
                          onChange={(e) => setForm({ ...form, emergency_contact_name: e.target.value })} placeholder="Contact name" />
                      </div>
                      <div>
                        <label className="label">Emergency Phone</label>
                        <input type="tel" className="input" value={form.emergency_contact_phone || ""}
                          onChange={(e) => setForm({ ...form, emergency_contact_phone: e.target.value })} placeholder="+91..." />
                      </div>
                      <div style={{ gridColumn: "1 / -1" }}>
                        <label className="label">Address</label>
                        <input type="text" className="input" value={form.address || ""}
                          onChange={(e) => setForm({ ...form, address: e.target.value })} />
                      </div>
                    </div>
                    <div style={{ marginTop: "1.5rem", display: "flex", justifyContent: "flex-end" }}>
                      <button type="submit" className="btn btn-primary" disabled={saving}>
                        {saving ? "Saving..." : "Save Profile Details"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>

              {/* Account Settings & Security */}
              <div className="card">
                <div className="card-header">
                  <h3 style={{ fontSize: "0.9375rem" }}>Account & Security</h3>
                </div>
                <div className="card-body">
                  <form onSubmit={saveAccount}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                      <div>
                        <label className="label">Full Name</label>
                        <input type="text" className="input" required value={accountForm.full_name || ""}
                          onChange={(e) => setAccountForm({ ...accountForm, full_name: e.target.value })} />
                      </div>
                      <div>
                        <label className="label">Email Address</label>
                        <input type="email" className="input" disabled value={account?.email || ""} style={{ background: "var(--border)", cursor: "not-allowed" }} />
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px", display: "block" }}>Email address cannot be changed.</span>
                      </div>
                      <div>
                        <label className="label">Phone Number</label>
                        <input type="tel" className="input" value={accountForm.phone || ""}
                          onChange={(e) => setAccountForm({ ...accountForm, phone: e.target.value })} placeholder="e.g. +91 9999999999" />
                      </div>
                      <div>
                        <label className="label">Language Preference</label>
                        <select className="input" value={accountForm.language_preference || "en"}
                          onChange={(e) => setAccountForm({ ...accountForm, language_preference: e.target.value })}>
                          <option value="en">English</option>
                          <option value="hi">Hindi (हिन्दी)</option>
                        </select>
                      </div>
                      <div>
                        <label className="label">Change Password</label>
                        <input type="password" className="input" value={accountForm.password || ""}
                          onChange={(e) => setAccountForm({ ...accountForm, password: e.target.value })} placeholder="Leave blank to keep current password" />
                      </div>
                    </div>
                    <div style={{ marginTop: "1.5rem", display: "flex", justifyContent: "flex-end" }}>
                      <button type="submit" className="btn btn-primary" disabled={savingAccount}>
                        {savingAccount ? "Updating..." : "Update Account"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>

            {/* Danger Zone */}
            <div className="card" style={{ border: "1px solid var(--danger)", background: "rgba(220, 38, 38, 0.02)" }}>
              <div className="card-header" style={{ borderBottom: "1px solid rgba(220, 38, 38, 0.1)" }}>
                <h3 style={{ color: "var(--danger)", fontSize: "0.9375rem", display: "flex", alignItems: "center", gap: "6px" }}>
                  <svg style={{ width: 16, height: 16 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Danger Zone
                </h3>
              </div>
              <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "1rem", borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.25rem" }}>Clear Chat History</div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Permanently delete all your AI medical chatbot conversations and messages.</div>
                  </div>
                  <button className="btn btn-ghost btn-sm" style={{ color: "var(--danger)", borderColor: "var(--danger)" }} onClick={handleClearChats}>Clear Chats</button>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "1rem", borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.25rem" }}>Clear Uploaded Reports</div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Remove all uploaded medical reports and parsed lab results from our servers.</div>
                  </div>
                  <button className="btn btn-ghost btn-sm" style={{ color: "var(--danger)", borderColor: "var(--danger)" }} onClick={handleClearReports}>Clear Reports</button>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.25rem", color: "var(--danger)" }}>Delete Account</div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Permanently delete your profile, clinical data, documents, and all active sessions. This cannot be undone.</div>
                  </div>
                  <button className="btn btn-danger btn-sm" onClick={handleDeleteAccount}>Delete Account</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Medical History Tab */}
        {activeTab === "history" && (
          <div className="card">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.9375rem" }}>Medical History</h3>
              <button className="btn btn-primary btn-sm" onClick={() => { setShowAddModal("history"); setAddForm({ status: "active" }); }}>+ Add</button>
            </div>
            {history.length === 0 ? (
              <div className="card-body" style={{ textAlign: "center", color: "var(--text-muted)", padding: "2rem" }}>No medical history recorded</div>
            ) : (
              <div className="table-container">
                <table>
                  <thead><tr><th>Condition</th><th>Status</th><th>Diagnosed</th><th>Notes</th><th style={{ width: 50 }}></th></tr></thead>
                  <tbody>
                    {history.map(h => (
                      <tr key={h.id}>
                        <td style={{ fontWeight: 500 }}>{h.condition}</td>
                        <td><span className={`badge ${h.status === "active" ? "badge-warning" : h.status === "resolved" ? "badge-success" : "badge-info"}`}>{h.status}</span></td>
                        <td style={{ color: "var(--text-secondary)" }}>{h.diagnosed_date ? new Date(h.diagnosed_date).toLocaleDateString() : "—"}</td>
                        <td style={{ color: "var(--text-secondary)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.notes || "—"}</td>
                        <td style={{ textAlign: "center" }}>
                          <button
                            onClick={() => handleDeleteItem("history", h.id)}
                            className="btn btn-ghost btn-sm"
                            style={{ color: "var(--danger)", padding: "0.25rem 0.5rem", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
                            title="Delete History"
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
        )}

        {/* Medications Tab */}
        {activeTab === "medications" && (
          <div className="card">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.9375rem" }}>Medications</h3>
              <button className="btn btn-primary btn-sm" onClick={() => { setShowAddModal("medication"); setAddForm({ is_active: true }); }}>+ Add</button>
            </div>
            {medications.length === 0 ? (
              <div className="card-body" style={{ textAlign: "center", color: "var(--text-muted)", padding: "2rem" }}>No medications recorded</div>
            ) : (
              <div className="table-container">
                <table>
                  <thead><tr><th>Name</th><th>Dosage</th><th>Frequency</th><th>Status</th><th style={{ width: 50 }}></th></tr></thead>
                  <tbody>
                    {medications.map(m => (
                      <tr key={m.id}>
                        <td style={{ fontWeight: 500 }}>{m.name}</td>
                        <td>{m.dosage || "—"}</td>
                        <td>{m.frequency || "—"}</td>
                        <td><span className={`badge ${m.is_active ? "badge-success" : "badge-info"}`}>{m.is_active ? "Active" : "Ended"}</span></td>
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
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Allergies Tab */}
        {activeTab === "allergies" && (
          <div className="card">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.9375rem" }}>Allergies</h3>
              <button className="btn btn-primary btn-sm" onClick={() => { setShowAddModal("allergy"); setAddForm({ severity: "moderate" }); }}>+ Add</button>
            </div>
            {allergies.length === 0 ? (
              <div className="card-body" style={{ textAlign: "center", color: "var(--text-muted)", padding: "2rem" }}>No allergies recorded</div>
            ) : (
              <div className="table-container">
                <table>
                  <thead><tr><th>Allergen</th><th>Severity</th><th>Reaction</th><th style={{ width: 50 }}></th></tr></thead>
                  <tbody>
                    {allergies.map(a => (
                      <tr key={a.id}>
                        <td style={{ fontWeight: 500 }}>{a.allergen}</td>
                        <td><span className={`badge ${a.severity === "severe" ? "badge-danger" : a.severity === "moderate" ? "badge-warning" : "badge-info"}`}>{a.severity}</span></td>
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
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Add Modal */}
        {showAddModal && (
          <div style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 50,
            display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem"
          }} onClick={() => setShowAddModal(null)}>
            <div className="card animate-fade-in-up" style={{ width: "100%", maxWidth: 480, padding: "1.5rem" }}
              onClick={(e) => e.stopPropagation()}>
              <h3 style={{ marginBottom: "1rem" }}>
                Add {showAddModal === "history" ? "Medical History" : showAddModal === "medication" ? "Medication" : "Allergy"}
              </h3>

              {showAddModal === "history" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <div><label className="label">Condition</label><input className="input" value={addForm.condition || ""} onChange={(e) => setAddForm({...addForm, condition: e.target.value})} /></div>
                  <div><label className="label">Status</label><select className="input" value={addForm.status || "active"} onChange={(e) => setAddForm({...addForm, status: e.target.value})}><option value="active">Active</option><option value="resolved">Resolved</option><option value="managed">Managed</option></select></div>
                  <div><label className="label">Diagnosed Date</label><input type="date" className="input" value={addForm.diagnosed_date || ""} onChange={(e) => setAddForm({...addForm, diagnosed_date: e.target.value})} /></div>
                  <div><label className="label">Notes</label><input className="input" value={addForm.notes || ""} onChange={(e) => setAddForm({...addForm, notes: e.target.value})} /></div>
                </div>
              )}

              {showAddModal === "medication" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <div><label className="label">Medication Name</label><input className="input" value={addForm.name || ""} onChange={(e) => setAddForm({...addForm, name: e.target.value})} /></div>
                  <div><label className="label">Dosage</label><input className="input" placeholder="e.g. 500mg" value={addForm.dosage || ""} onChange={(e) => setAddForm({...addForm, dosage: e.target.value})} /></div>
                  <div><label className="label">Frequency</label><input className="input" placeholder="e.g. Twice daily" value={addForm.frequency || ""} onChange={(e) => setAddForm({...addForm, frequency: e.target.value})} /></div>
                </div>
              )}

              {showAddModal === "allergy" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <div><label className="label">Allergen</label><input className="input" value={addForm.allergen || ""} onChange={(e) => setAddForm({...addForm, allergen: e.target.value})} /></div>
                  <div><label className="label">Severity</label><select className="input" value={addForm.severity || "moderate"} onChange={(e) => setAddForm({...addForm, severity: e.target.value})}><option value="mild">Mild</option><option value="moderate">Moderate</option><option value="severe">Severe</option></select></div>
                  <div><label className="label">Reaction</label><input className="input" value={addForm.reaction || ""} onChange={(e) => setAddForm({...addForm, reaction: e.target.value})} /></div>
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1.25rem" }}>
                <button className="btn btn-secondary" onClick={() => setShowAddModal(null)}>Cancel</button>
                <button className="btn btn-primary" onClick={addItem}>Save</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
