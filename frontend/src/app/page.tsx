"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const user = api.getUser();
    if (user) {
      router.push("/chat");
    } else {
      router.push("/login");
    }
  }, [router]);

  return (
    <div className="auth-page">
      <div style={{ textAlign: "center" }}>
        <div className="animate-spin" style={{
          width: 40, height: 40, border: "3px solid var(--border)",
          borderTopColor: "var(--primary)", borderRadius: "50%", margin: "0 auto 1rem"
        }} />
        <p style={{ color: "var(--text-secondary)" }}>Loading MedAI Assistant...</p>
      </div>
    </div>
  );
}
