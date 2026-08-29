import { useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import { Activity, Lock, User, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Login failed");
      }
      const data = await res.json();
      localStorage.setItem("medirag_token", data.access_token);
      toast.success("Welcome to MediRAG AI");
      router.push("/chat");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head><title>Login – MediRAG AI</title></Head>
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", background: "#0d0f1a", padding: "24px",
      }}>
        <div style={{
          background: "#1a1d27", border: "1px solid #2a2d3e", borderRadius: "16px",
          padding: "48px 40px", width: "100%", maxWidth: "420px",
          boxShadow: "0 25px 50px rgba(0,0,0,0.5)",
        }}>
          {/* Logo */}
          <div style={{ textAlign: "center", marginBottom: "32px" }}>
            <div style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              width: "64px", height: "64px", background: "linear-gradient(135deg, #4f8ef7, #7c3aed)",
              borderRadius: "16px", marginBottom: "16px",
            }}>
              <Activity size={32} color="white" />
            </div>
            <h1 style={{ color: "#e8eaf0", fontSize: "24px", fontWeight: 700, margin: 0 }}>MediRAG AI</h1>
            <p style={{ color: "#6b7280", fontSize: "14px", marginTop: "8px" }}>
              Enterprise Healthcare Knowledge Assistant
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: "16px" }}>
              <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>
                Username
              </label>
              <div style={{ position: "relative" }}>
                <User size={16} color="#6b7280" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="Enter username"
                  required
                  style={{
                    width: "100%", padding: "10px 12px 10px 36px",
                    background: "#0d0f1a", border: "1px solid #2a2d3e",
                    borderRadius: "8px", color: "#e8eaf0", fontSize: "14px",
                    outline: "none", boxSizing: "border-box",
                  }}
                />
              </div>
            </div>

            <div style={{ marginBottom: "24px" }}>
              <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>
                Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock size={16} color="#6b7280" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter password"
                  required
                  style={{
                    width: "100%", padding: "10px 12px 10px 36px",
                    background: "#0d0f1a", border: "1px solid #2a2d3e",
                    borderRadius: "8px", color: "#e8eaf0", fontSize: "14px",
                    outline: "none", boxSizing: "border-box",
                  }}
                />
              </div>
            </div>

            {error && (
              <div style={{
                display: "flex", alignItems: "center", gap: "8px",
                color: "#ef4444", fontSize: "13px", marginBottom: "16px",
                padding: "10px 12px", background: "rgba(239,68,68,0.1)",
                borderRadius: "8px", border: "1px solid rgba(239,68,68,0.2)",
              }}>
                <AlertCircle size={14} />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                width: "100%", padding: "12px",
                background: loading ? "#374151" : "linear-gradient(135deg, #4f8ef7, #7c3aed)",
                color: "white", border: "none", borderRadius: "8px",
                fontSize: "15px", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
                transition: "opacity 0.2s",
              }}
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p style={{ color: "#4b5563", fontSize: "12px", textAlign: "center", marginTop: "24px" }}>
            Educational use only. Not a substitute for clinical judgment.
          </p>
        </div>
      </div>
    </>
  );
}
