"use client";
import { useEffect, useState, useRef, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(true);
  
  // UI states
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [greeting, setGreeting] = useState("Good day");

  // In-Memory Document Extraction states
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState<string>("");
  const [extracting, setExtracting] = useState(false);

  // Prompt Cards
  const [promptCards, setPromptCards] = useState<string[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const promptOptions = [
    "Explain the interaction between Metformin and Rifampicin.",
    "How do Omeprazole and Clopidogrel interact?",
    "Describe the transporter interaction between Simvastatin and Gemfibrozil.",
    "Discuss the mechanism of Dolutegravir-induced Metformin systemic elevation."
  ];

  useEffect(() => {
    // Auth Check
    const u = api.getUser();
    if (!u) {
      router.push("/login");
    } else {
      setUser(u);
    }

    // Set greeting based on time of day
    const hour = new Date().getHours();
    if (hour < 12) setGreeting("Good morning");
    else if (hour < 17) setGreeting("Good afternoon");
    else setGreeting("Good evening");

    // Load initial prompt cards
    setPromptCards(promptOptions);

    // Initialize theme
    const savedTheme = localStorage.getItem("theme");
    const isDark = savedTheme === "dark";
    setIsDarkMode(isDark);
    if (isDark) {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }, [router]);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadSessions = async () => {
    try {
      const s = await api.getChatSessions();
      setSessions(s);
      if (s.length > 0) {
        selectSession(s[0].id);
      }
    } catch { }
    setLoadingSessions(false);
  };

  const selectSession = async (sessionId: string) => {
    setActiveSession(sessionId);
    setSidebarOpen(false);
    try {
      const msgs = await api.getChatMessages(sessionId);
      setMessages(msgs);
    } catch { setMessages([]); }
  };

  const createNewSession = async () => {
    try {
      const session = await api.createChatSession();
      setSessions(prev => [session, ...prev]);
      setActiveSession(session.id);
      setMessages([]);
      setSidebarOpen(false);
    } catch { }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await api.deleteChatSession(sessionId);
      setSessions(prev => {
        const next = prev.filter(s => s.id !== sessionId);
        if (activeSession === sessionId) {
          if (next.length > 0) {
            selectSession(next[0].id);
          } else {
            setActiveSession(null);
            setMessages([]);
          }
        }
        return next;
      });
    } catch (err: any) {
      alert(err.message || "Failed to delete conversation");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    // Increase size limit to 50MB to support large browser memory uploads
    if (file.size > 50 * 1024 * 1024) {
      alert("File too large. Maximum size allowed is 50MB.");
      return;
    }

    setAttachedFile(file);
    setExtracting(true);
    setExtractedText("");

    const isTextFile = 
      file.type.startsWith("text/") || 
      file.name.endsWith(".txt") || 
      file.name.endsWith(".csv") || 
      file.name.endsWith(".md") || 
      file.name.endsWith(".json");

    if (isTextFile) {
      // 100% Client-Side memory extraction
      const reader = new FileReader();
      reader.onload = (evt) => {
        setExtractedText((evt.target?.result as string) || "");
        setExtracting(false);
      };
      reader.onerror = () => {
        alert("Failed to read text file directly in browser memory.");
        setExtracting(false);
        setAttachedFile(null);
      };
      reader.readAsText(file);
    } else {
      // PDF or Image: extract statelessly in backend memory (does NOT store on DB)
      api.extractDocumentText(file)
        .then((res) => {
          setExtractedText(res.text || "");
          setExtracting(false);
        })
        .catch((err) => {
          alert(`Document extraction failed: ${err.message || "Unknown error"}`);
          setExtracting(false);
          setAttachedFile(null);
        });
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const performSendMessage = async (content: string) => {
    if ((!content.trim() && !attachedFile) || sending) return;
    if (extracting) {
      alert("Please wait until document text extraction finishes.");
      return;
    }

    setSending(true);
    let finalContent = content;
    const fileToUpload = attachedFile;
    const extractedContent = extractedText;

    // Reset attached file state right away
    setAttachedFile(null);
    setExtractedText("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    setInput("");

    // Auto-create chat session if none is active
    let currentSessionId = activeSession;
    if (!currentSessionId) {
      try {
        const title = fileToUpload ? `Document: ${fileToUpload.name}` : content.slice(0, 50);
        const session = await api.createChatSession(title);
        setSessions(prev => [session, ...prev]);
        setActiveSession(session.id);
        currentSessionId = session.id;
      } catch (err: any) {
        alert("Failed to start a new chat session: " + (err.message || "Unknown error"));
        setSending(false);
        return;
      }
    }

    // Format final message payload to send to LLM context
    if (fileToUpload) {
      if (extractedContent && extractedContent.trim()) {
        finalContent = `[Attached Medical Report: ${fileToUpload.name}]\n\n--- Extracted Document Content ---\n${extractedContent}\n----------------------------------\n\nUser Message: ${content}`;
      } else {
        finalContent = `[Attached Medical Report: ${fileToUpload.name}]\n\n(No text could be extracted from this document)\n\nUser Message: ${content}`;
      }
    }

    // Add user message optimistically
    const tempText = fileToUpload 
      ? `[Attached Medical Report: ${fileToUpload.name}]\nUser Message: ${content}`
      : content;

    const tempUserMsg = { 
      id: "temp-user", 
      role: "user", 
      content: tempText, 
      created_at: new Date().toISOString() 
    };
    
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const result = await api.sendMessage(currentSessionId, finalContent);
      setMessages(prev => [
        ...prev.filter(m => m.id !== "temp-user"),
        result.user_message,
        result.ai_message
      ]);
      
      const sidebarTitle = fileToUpload 
        ? `Document: ${fileToUpload.name}`
        : content.slice(0, 50);

      setSessions(prev => prev.map(s =>
        s.id === currentSessionId ? { ...s, title: sidebarTitle, message_count: (s.message_count || 0) + 2 } : s
      ));
    } catch (err: any) {
      setMessages(prev => prev.filter(m => m.id !== "temp-user"));
      alert(err.message || "Failed to send message. Please check your backend server logs.");
    }

    setSending(false);
    textareaRef.current?.focus();
  };

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    await performSendMessage(input.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(e as any);
    }
  };

  const toggleTheme = (dark: boolean) => {
    setIsDarkMode(dark);
    if (dark) {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("theme", "light");
    }
  };

  const parseMessageContent = (content: string) => {
    if (content && content.startsWith("[Attached Medical Report: ")) {
      const lines = content.split("\n");
      const headerLine = lines[0];
      const fileName = headerLine.replace("[Attached Medical Report: ", "").replace("]", "");
      
      const userMessageIndex = content.indexOf("User Message: ");
      let userText = "";
      if (userMessageIndex !== -1) {
        userText = content.substring(userMessageIndex + "User Message: ".length).trim();
      } else {
        userText = content;
      }
      return {
        hasAttachment: true,
        fileName,
        text: userText
      };
    }
    return {
      hasAttachment: false,
      fileName: "",
      text: content
    };
  };

  if (!user) {
    return (
      <div className="auth-page">
        <div className="animate-spin" style={{
          width: 40, height: 40, border: "3px solid var(--border)",
          borderTopColor: "var(--primary)", borderRadius: "50%"
        }} />
      </div>
    );
  }

  const userInitials = user.full_name
    ? user.full_name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()
    : "US";

  const firstName = user.full_name ? user.full_name.split(" ")[0] : "User";
  const activeSessionTitle = sessions.find(s => s.id === activeSession)?.title || "AI Consultation";

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", overflow: "hidden", position: "relative" }} className="think-layout-root">
      
      {/* Background Radial Glow */}
      <div className="radial-background-glow" />

      {/* Hidden file input */}
      <input 
        type="file" 
        ref={fileInputRef} 
        style={{ display: "none" }} 
        onChange={handleFileChange} 
        accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.md,.json" 
      />

      {/* Mobile/Sidebar Overlay */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: "fixed", inset: 0, background: "transparent",
            zIndex: 35
          }}
          className="mobile-sidebar-overlay"
        />
      )}

      {/* ChatGPT / Claude Sidebar */}
      <aside 
        style={{
          width: sidebarOpen ? 260 : 0,
          opacity: sidebarOpen ? 1 : 0,
          overflow: "hidden",
          background: "var(--bg-sidebar)",
          borderRight: sidebarOpen ? "1px solid var(--border)" : "none",
          display: "flex",
          flexDirection: "column",
          height: "100%",
          flexShrink: 0,
          zIndex: 38,
          transition: "width 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s, border 0.2s"
        }}
        className={`chat-sidebar-responsive ${sidebarOpen ? "sidebar-mobile-open" : ""}`}
      >
        {/* Brand Logo & New Chat */}
        <div style={{ padding: "1.25rem 1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.25rem 0" }}>
            <span style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--text)", letterSpacing: "-0.02em" }}>PharmaGPT</span>
          </div>
          
          <button 
            onClick={createNewSession}
            style={{
              width: "100%",
              padding: "0.625rem 0.875rem",
              borderRadius: "var(--radius-lg)",
              background: "var(--bg-card)",
              border: "1px solid var(--border-dark)",
              color: "var(--text)",
              fontWeight: 600,
              fontSize: "0.8125rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              cursor: "pointer",
              transition: "all 0.15s"
            }}
          >
            <span>+</span> New Chat
          </button>
        </div>

        {/* Chat History Sessions List */}
        <div style={{ flex: 1, overflowY: "auto", padding: "0 0.5rem" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", padding: "0.5rem 0.5rem 0.375rem" }}>
            History
          </div>
          {loadingSessions ? (
            <div style={{ padding: "1rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.75rem" }}>Loading...</div>
          ) : sessions.length === 0 ? (
            <div style={{ padding: "1rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.75rem" }}>
              No past chats.
            </div>
          ) : (
            sessions.map(s => (
              <div key={s.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderRadius: "var(--radius-sm)",
                  marginBottom: "2px",
                  background: activeSession === s.id ? "var(--border)" : "transparent",
                  transition: "all 0.1s"
                }}
                className="chat-session-row"
              >
                <button 
                  onClick={() => selectSession(s.id)}
                  style={{
                    flex: 1,
                    textAlign: "left",
                    padding: "0.5rem 0.625rem",
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    fontSize: "0.8125rem",
                    fontWeight: activeSession === s.id ? 600 : 400,
                    color: activeSession === s.id ? "var(--text)" : "var(--text-secondary)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap"
                  }}
                >
                  {s.title || "Untitled Conversation"}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    padding: "0.25rem",
                    cursor: "pointer",
                    marginRight: "4px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    opacity: activeSession === s.id ? 0.8 : 0
                  }}
                  className="chat-delete-icon-btn"
                  title="Delete Conversation"
                >
                  <svg style={{ width: 12, height: 12 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))
          )}
        </div>

        {/* Sidebar Footer — Theme & Account Profile */}
        <div style={{ padding: "0.75rem 1rem", borderTop: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {/* Theme switcher */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)" }}>Theme</span>
            <div style={{ display: "flex", background: "var(--border)", borderRadius: "var(--radius-sm)", padding: "2px" }}>
              <button 
                onClick={() => toggleTheme(false)} 
                style={{
                  background: !isDarkMode ? "var(--bg-card)" : "transparent",
                  border: "none",
                  padding: "0.25rem 0.5rem",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center"
                }}
                title="Light Mode"
              >
                <svg style={{ width: 12, height: 12, color: !isDarkMode ? "var(--primary)" : "var(--text-muted)" }} fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
                </svg>
              </button>
              <button 
                onClick={() => toggleTheme(true)} 
                style={{
                  background: isDarkMode ? "var(--bg-card)" : "transparent",
                  border: "none",
                  padding: "0.25rem 0.5rem",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center"
                }}
                title="Dark Mode"
              >
                <svg style={{ width: 12, height: 12, color: isDarkMode ? "var(--primary)" : "var(--text-muted)" }} fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              </button>
            </div>
          </div>

          {/* User profile */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 0 }}>
              <div className="think-profile-avatar">{userInitials}</div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {user.full_name}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "capitalize" }}>
                  {user.role}
                </div>
              </div>
            </div>
            
            <button 
              onClick={() => api.logout()} 
              style={{
                background: "transparent", border: "none", color: "var(--text-muted)",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center"
              }}
              title="Sign Out"
            >
              <svg style={{ width: 16, height: 16 }} fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>

      </aside>

      {/* Main Workspace Panel */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", position: "relative", zIndex: 10 }}>
        
        {/* Top Control Bar */}
        <header style={{
          height: 56,
          display: "flex",
          alignItems: "center",
          padding: "0 1.5rem",
          justifyContent: "space-between"
        }}>
          {/* Sidebar Toggle & Title */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text)",
                cursor: "pointer",
                display: "flex",
                padding: "6px",
                borderRadius: "var(--radius-sm)",
                transition: "background 0.15s"
              }}
              className="sidebar-toggle-btn"
              title="Toggle Sidebar"
            >
              <svg style={{ width: 18, height: 18 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 5h18v14H3zM9 5v14" />
              </svg>
            </button>
            <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.01em" }} className="think-header-title">
              {activeSession ? activeSessionTitle : "PharmaGPT"}
            </span>
          </div>

          <div className="think-top-avatar" title={user.full_name}>
            {userInitials}
          </div>
        </header>

        {/* Chat Content Space */}
        {!activeSession ? (
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "2rem 1.5rem 140px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center"
          }}>
            
            <h1 className="think-greeting-header" style={{ marginBottom: "0.5rem" }}>
              {greeting}, {firstName}
            </h1>
            <h2 className="think-greeting-subheader" style={{ marginBottom: "2.5rem" }}>
              How can I help you today?
            </h2>

            {/* 4 Prompt Cards Grid */}
            <div className="think-prompt-grid">
              {promptCards.map((q, idx) => (
                <button 
                  key={idx} 
                  onClick={() => { setInput(q); textareaRef.current?.focus(); }}
                  className="think-prompt-card"
                >
                  {q}
                </button>
              ))}
            </div>

          </div>
        ) : (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", position: "relative" }}>
            
            {/* Scrollable Message List */}
            <div 
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "1rem 1.5rem 130px", 
                display: "flex",
                flexDirection: "column",
                alignItems: "center"
              }}
            >
              <div style={{ width: "100%", maxWidth: 768, display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                
                {messages.length === 0 && (
                  <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: "4rem" }}>
                    <p style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text)", marginBottom: "0.5rem" }}>New Consultation Session</p>
                    <p style={{ fontSize: "0.8125rem", maxWidth: 420, margin: "0 auto 1.5rem", lineHeight: 1.5 }}>
                      Type a pharmacology interaction question or choose a scenario to start the grounded verification.
                    </p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", justifyContent: "center" }}>
                      {[
                        "Explain the interaction between Metformin and Rifampicin.",
                        "How do Omeprazole and Clopidogrel interact?",
                        "Discuss the Digoxin and Verapamil transport interaction."
                      ].map(q => (
                        <button 
                          key={q} 
                          onClick={() => { setInput(q); textareaRef.current?.focus(); }}
                          className="think-prompt-card"
                          style={{ margin: 0, padding: "0.5rem 0.875rem", fontSize: "0.75rem", display: "inline-block" }}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((msg) => {
                  const parsed = parseMessageContent(msg.content);
                  
                  return (
                    <div 
                      key={msg.id}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        padding: "1.25rem",
                        borderRadius: "var(--radius-lg)",
                        background: msg.role === "user" ? "var(--bg-card)" : "transparent",
                        border: msg.role === "user" ? "1px solid var(--border)" : "none",
                        alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                        width: msg.role === "user" ? "85%" : "100%",
                        transition: "all 0.15s"
                      }}
                    >
                      {/* Speaker Header */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: msg.role === "user" ? "var(--primary)" : "var(--success)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.03em" }}>
                          {msg.role === "user" ? "You" : "PharmaGPT"}
                        </div>
                      </div>

                      {/* Attachment Tag (in bubble) */}
                      {parsed.hasAttachment && (
                        <div style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          background: "var(--bg-sidebar)",
                          border: "1px solid var(--border)",
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm)",
                          marginBottom: "0.75rem",
                          width: "fit-content",
                          fontSize: "0.75rem",
                          color: "var(--text-secondary)"
                        }}>
                          <svg style={{ width: 14, height: 14, color: "var(--primary)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636l-3.536 3.536m0 0l-5.656 5.656a4.002 4.002 0 11-5.656-5.656l8.485-8.485a6.002 6.002 0 118.485 8.485l-7.071 7.07a8.002 8.002 0 11-11.314-11.314l4.243-4.242" />
                          </svg>
                          <span>Attached: <strong>{parsed.fileName}</strong></span>
                        </div>
                      )}

                      {/* Factual Answer Body */}
                      <div style={{ whiteSpace: "pre-wrap", fontSize: "0.875rem", lineHeight: 1.6, color: "var(--text)" }}>
                        {parsed.text}
                      </div>

                      {/* Clean References Panel */}
                      {msg.role === "assistant" && msg.metadata_json && (
                        (() => {
                          try {
                            const meta = JSON.parse(msg.metadata_json);
                            if (!meta.references || meta.references.length === 0) return null;
                            return (
                              <details className="references-section" style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.75rem", borderTop: "1px solid var(--border)", paddingTop: "0.5rem" }}>
                                <summary style={{ cursor: "pointer", fontWeight: 600 }}>References ({meta.references.length})</summary>
                                <ul style={{ listStyle: "none", paddingLeft: 0, marginTop: "0.25rem" }}>
                                  {meta.references.map((ref: any, idx: number) => (
                                    <li key={idx} style={{ display: "flex", gap: "6px", marginBottom: "4px" }}>
                                      <span>[{idx + 1}]</span>
                                      <a href={ref.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--primary)", textDecoration: "none" }}>{ref.title || ref.url}</a>
                                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", background: "var(--border)", padding: "0 4px", borderRadius: 2 }}>{ref.source}</span>
                                    </li>
                                  ))}
                                </ul>
                              </details>
                            );
                          } catch {
                            return null;
                          }
                        })()
                      )}

                    </div>
                  );
                })}

                {sending && (
                  <div style={{ display: "flex", gap: "0.375rem", padding: "1rem" }}>
                    <span className="animate-pulse" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--primary)" }} />
                    <span className="animate-pulse" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--primary)", animationDelay: "0.15s" }} />
                    <span className="animate-pulse" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--primary)", animationDelay: "0.3s" }} />
                  </div>
                )}
                
                {extracting && (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "1rem", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                    <span className="animate-spin" style={{ width: 14, height: 14, borderRadius: "50%", border: "2px solid var(--border)", borderTopColor: "var(--primary)" }} />
                    Extracting document content into browser memory...
                  </div>
                )}

                <div ref={messagesEndRef} />

              </div>
            </div>

          </div>
        )}

        {/* Bottom Fixed Text Box (matches ThinkAI but simplified) */}
        <div 
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            background: "linear-gradient(to top, var(--bg) 60%, transparent 100%)",
            padding: "2rem 1.5rem 1.25rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            pointerEvents: "none",
            zIndex: 30
          }}
        >
          <div style={{ width: "100%", maxWidth: 768, display: "flex", flexDirection: "column", gap: "0.625rem", pointerEvents: "auto" }}>
            
            {/* Custom styled flat input box */}
            <div className="think-input-container">
              
              {/* Attachment Preview Box */}
              {attachedFile && (
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  background: "var(--bg-sidebar)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  padding: "6px 12px",
                  marginBottom: "8px",
                  width: "fit-content"
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg style={{ width: 14, height: 14, color: "var(--primary)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636l-3.536 3.536m0 0l-5.656 5.656a4.002 4.002 0 11-5.656-5.656l8.485-8.485a6.002 6.002 0 118.485 8.485l-7.071 7.07a8.002 8.002 0 11-11.314-11.314l4.243-4.242" />
                    </svg>
                    <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                      {attachedFile.name}
                    </span>
                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                      ({(attachedFile.size / 1024).toFixed(1)} KB)
                    </span>
                    {extracting ? (
                      <span style={{ fontSize: "0.6875rem", color: "var(--warning)", fontStyle: "italic", marginLeft: "4px" }}>
                        (Extracting...)
                      </span>
                    ) : (
                      <span style={{ fontSize: "0.6875rem", color: "var(--success)", fontWeight: 600, marginLeft: "4px" }}>
                        (Extracted in Memory)
                      </span>
                    )}
                  </div>
                  
                  <button
                    type="button"
                    onClick={() => {
                      setAttachedFile(null);
                      setExtractedText("");
                    }}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      marginLeft: "8px",
                      fontSize: "1.1rem",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}
                    title="Remove file"
                  >
                    ×
                  </button>
                </div>
              )}

              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={activeSession ? "Ask a pharmacology query or drug interaction scenario..." : "How can PharmaGPT help you today?"}
                rows={1}
                disabled={sending}
                style={{
                  width: "100%",
                  border: "none",
                  outline: "none",
                  background: "transparent",
                  color: "var(--text)",
                  resize: "none",
                  minHeight: 24,
                  maxHeight: 180,
                  fontSize: "0.875rem",
                  lineHeight: 1.4,
                  padding: "0"
                }}
              />
              
              {/* Bottom Row inside input container */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem", borderTop: "1px solid var(--border)", paddingTop: "0.75rem" }}>
                
                {/* Left: Attachment trigger clip */}
                <button 
                  type="button" 
                  className="think-utility-btn" 
                  title="Add medical report (PDF, Image, or Text)"
                  onClick={triggerFileInput}
                  style={{
                    height: 28,
                    width: 28,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                  }}
                >
                  <svg style={{ width: 15, height: 15 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636l-3.536 3.536m0 0l-5.656 5.656a4.002 4.002 0 11-5.656-5.656l8.485-8.485a6.002 6.002 0 118.485 8.485l-7.071 7.07a8.002 8.002 0 11-11.314-11.314l4.243-4.242" />
                  </svg>
                </button>

                {/* Right: Submit button */}
                <button 
                  type="button"
                  onClick={sendMessage}
                  disabled={sending || (!input.trim() && !attachedFile) || extracting}
                  style={{
                    height: 28,
                    width: 28,
                    borderRadius: "50%",
                    background: sending || (!input.trim() && !attachedFile) || extracting ? "transparent" : "var(--primary)",
                    color: sending || (!input.trim() && !attachedFile) || extracting ? "var(--text-muted)" : "white",
                    border: "none",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: sending || (!input.trim() && !attachedFile) || extracting ? "default" : "pointer",
                    transition: "all 0.15s"
                  }}
                >
                  <svg style={{ width: 12, height: 12 }} fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
                  </svg>
                </button>
              </div>

            </div>
            
            {/* Footer disclaimer */}
            <div style={{ display: "flex", justifyContent: "center", padding: "0 0.5rem", fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              <span>PharmaGPT can make mistakes. Please double-check responses.</span>
            </div>
          </div>
        </div>

      </main>

      <style>{`
        /* ── ChatGPT / Claude sidebar responsiveness ── */
        @media (max-width: 768px) {
          .chat-sidebar-responsive {
            position: fixed !important;
            left: 0;
            top: 0;
            bottom: 0;
            width: 260px !important;
            transform: translateX(-100%);
            box-shadow: none !important;
            z-index: 40 !important;
            opacity: 1 !important;
          }
          .sidebar-mobile-open {
            transform: translateX(0) !important;
          }
          .mobile-chat-header {
            display: flex !important;
          }
          .think-greeting-header {
            font-size: 1.875rem !important;
          }
          .think-greeting-subheader {
            font-size: 1.5rem !important;
          }
          .think-prompt-grid {
            grid-template-columns: 1fr !important;
            gap: 0.5rem !important;
            width: 100% !important;
            padding: 0 1rem !important;
          }
          .think-input-container {
            border-radius: var(--radius) !important;
            padding: 10px !important;
          }
        }
      `}</style>
    </div>
  );
}
