import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import { Upload, CheckCircle, AlertCircle, ArrowLeft, FileText } from "lucide-react";
import toast from "react-hot-toast";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://rag-based-medical-question-answering.onrender.com";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [category, setCategory] = useState("medical_pdfs");

  useEffect(() => {
    // No auth required
  }, [router]);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (category) formData.append("source", category);
      const res = await fetch(`${API_URL}/api/v1/documents/upload-document`, {
        method: "POST",
        headers: {},
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed (${res.status})`);
      }
      toast.success("Document uploaded and indexed successfully");
      setFile(null);
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <Head><title>Upload – MediRAG AI</title></Head>
      <div style={{ minHeight: "100vh", background: "#0d0f1a", padding: "24px" }}>
        <div style={{ maxWidth: "600px", margin: "0 auto" }}>
          <button onClick={() => router.push("/chat")} style={{
            display: "flex", alignItems: "center", gap: "6px",
            color: "#9ca3af", background: "none", border: "none",
            cursor: "pointer", fontSize: "14px", marginBottom: "24px",
          }}>
            <ArrowLeft size={16} /> Back to Chat
          </button>

          <h1 style={{ color: "#e8eaf0", fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>
            Upload Documents
          </h1>
          <p style={{ color: "#6b7280", fontSize: "14px", marginBottom: "32px" }}>
            Upload medical PDFs, treatment guidelines, or research articles to your knowledge base.
          </p>

          <div style={{ background: "#1a1d27", border: "1px solid #2a2d3e", borderRadius: "16px", padding: "24px" }}>
            <div style={{ marginBottom: "20px" }}>
              <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>Category</label>
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                style={{
                  width: "100%", padding: "10px 12px", background: "#0d0f1a",
                  border: "1px solid #2a2d3e", borderRadius: "8px", color: "#e8eaf0", fontSize: "14px",
                  outline: "none",
                }}
              >
                <option value="medical_pdfs">Medical PDFs</option>
                <option value="treatment_guidelines">Treatment Guidelines</option>
                <option value="drug_databases">Drug Databases</option>
                <option value="research_articles">Research Articles</option>
                <option value="medical_books">Medical Books</option>
                <option value="clinical_protocols">Clinical Protocols</option>
              </select>
            </div>

            <div
              onClick={() => document.getElementById("file-input")?.click()}
              style={{
                border: "2px dashed #2a2d3e", borderRadius: "12px", padding: "40px",
                textAlign: "center", cursor: "pointer",
                background: file ? "rgba(79,142,247,0.05)" : "transparent",
                transition: "background 0.2s",
              }}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.txt"
                style={{ display: "none" }}
                onChange={e => setFile(e.target.files?.[0] || null)}
              />
              {file ? (
                <div>
                  <CheckCircle size={40} color="#4f8ef7" style={{ marginBottom: "12px" }} />
                  <div style={{ color: "#e8eaf0", fontWeight: 600 }}>{file.name}</div>
                  <div style={{ color: "#6b7280", fontSize: "13px" }}>
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
              ) : (
                <div>
                  <Upload size={40} color="#4b5563" style={{ marginBottom: "12px" }} />
                  <div style={{ color: "#9ca3af", fontWeight: 600 }}>Click to select a file</div>
                  <div style={{ color: "#4b5563", fontSize: "13px" }}>PDF, DOCX, or TXT (max 50MB)</div>
                </div>
              )}
            </div>

            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              style={{
                marginTop: "20px", width: "100%", padding: "12px",
                background: !file || uploading ? "#374151" : "linear-gradient(135deg, #4f8ef7, #7c3aed)",
                border: "none", borderRadius: "8px", color: "white",
                fontSize: "15px", fontWeight: 600, cursor: !file || uploading ? "not-allowed" : "pointer",
              }}
            >
              {uploading ? "Uploading & Indexing..." : "Upload Document"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
