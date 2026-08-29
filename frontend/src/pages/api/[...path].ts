/**
 * Next.js catch-all API proxy — forwards all /api/* requests to the Render backend.
 * Eliminates browser CORS issues: browser → Vercel (same origin) → Render (server-side).
 */
import type { NextApiRequest, NextApiResponse } from "next";

const BACKEND = "https://rag-based-medical-question-answering.onrender.com";

export const config = {
  api: {
    bodyParser: {
      sizeLimit: "10mb",
    },
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const pathSegments = req.query.path;
  const pathStr = Array.isArray(pathSegments) ? pathSegments.join("/") : pathSegments || "";
  const targetUrl = `${BACKEND}/api/${pathStr}`;

  try {
    const headers: Record<string, string> = {};
    if (req.headers["content-type"]) {
      headers["content-type"] = req.headers["content-type"] as string;
    }
    if (req.headers["authorization"]) {
      headers["authorization"] = req.headers["authorization"] as string;
    }

    const fetchOptions: RequestInit = {
      method: req.method,
      headers,
    };

    if (req.method !== "GET" && req.method !== "HEAD") {
      fetchOptions.body = JSON.stringify(req.body);
    }

    const backendRes = await fetch(targetUrl, fetchOptions);
    const data = await backendRes.json().catch(() => ({}));

    res.status(backendRes.status).json(data);
  } catch (err: any) {
    res.status(502).json({ detail: `Proxy error: ${err.message}` });
  }
}
