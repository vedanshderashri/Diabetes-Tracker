"use client";
import { useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

const NAV_ITEMS = [
  {
    href: "/chat",
    label: "AI Chat",
    icon: (
      <svg style={{ width: 18, height: 18, flexShrink: 0 }} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    )
  },
  {
    href: "/reports",
    label: "Reports",
    icon: (
      <svg style={{ width: 18, height: 18, flexShrink: 0 }} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    )
  },
  {
    href: "/doctor-summary",
    label: "Doctor Summary",
    icon: (
      <svg style={{ width: 18, height: 18, flexShrink: 0 }} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    )
  }
];

const ADMIN_ITEMS = [
  {
    href: "/admin",
    label: "Admin Panel",
    icon: (
      <svg style={{ width: 18, height: 18, flexShrink: 0 }} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    )
  }
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [mailOpen, setMailOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [messages, setMessages] = useState<any[]>([]);

  useEffect(() => {
    const u = api.getUser();
    if (!u) {
      router.push("/login");
    } else {
      setUser(u);
    }

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
    if (!user) return;
    
    // Fetch notifications and message previews from active endpoints
    const fetchHeaderData = async () => {
      try {
        const [dash, sessions, reportsList] = await Promise.all([
          api.getDashboard().catch(() => null),
          api.getChatSessions().catch(() => []),
          api.getReports().catch(() => [])
        ]);

        // Mapped notifications
        const mappedIndicators = (dash?.risk_indicators || []).map((ri: any, idx: number) => ({
          id: `risk-${idx}`,
          type: "warning",
          title: ri.level === "high" ? "Critical Risk Alert" : "Health Warning",
          message: ri.message,
          date: "Recent",
          read: false
        }));

        const mappedReports = (reportsList || []).slice(0, 2).map((r: any) => ({
          id: `report-${r.id}`,
          type: "report",
          title: "Report Analyzed",
          message: `Medical report ${r.file_name.slice(0, 16)}${r.file_name.length > 16 ? "..." : ""} is analyzed.`,
          date: new Date(r.upload_date).toLocaleDateString([], { month: "short", day: "numeric" }),
          read: false
        }));

        const finalNotifs = [...mappedIndicators, ...mappedReports];
        if (finalNotifs.length === 0) {
          finalNotifs.push({
            id: "sys-welcome",
            type: "system",
            title: "VitalHealth Active",
            message: "Welcome back! Keep monitoring your vitals.",
            date: "Just now",
            read: true
          });
        }
        setNotifications(finalNotifs);

        // Mapped messages from chat sessions
        const defaultMessages = [
          { id: "msg-1", sender: "AI Consultant", preview: "Welcome to VitalHealth! Start a chat session.", date: "Now", href: "/chat" },
          { id: "msg-2", sender: "System Notification", preview: "Diabetes Risk Prediction Model v1.2 is active.", date: "1 day ago", href: "/dashboard" }
        ];

        if (sessions && sessions.length > 0) {
          const mappedSessions = sessions.slice(0, 3).map((s: any) => ({
            id: s.id,
            sender: "AI Session",
            preview: s.title || "Consultation in progress",
            date: new Date(s.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            href: `/chat`
          }));
          setMessages(mappedSessions);
        } else {
          setMessages(defaultMessages);
        }
      } catch (e) {}
    };
    fetchHeaderData();
  }, [user]);

  // Click outside dropdowns closing
  useEffect(() => {
    const clickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest(".app-header-actions") && !target.closest(".dropdown-menu")) {
        setNotifOpen(false);
        setMailOpen(false);
      }
    };
    document.addEventListener("mousedown", clickOutside);
    return () => document.removeEventListener("mousedown", clickOutside);
  }, []);

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

  const handleClearNotification = (id: any) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const handleClearAllNotifications = () => {
    setNotifications([]);
  };


  return (
    <div className="app-layout" style={{ minHeight: "100vh", background: "var(--bg)" }}>
      {children}
    </div>
  );
}
