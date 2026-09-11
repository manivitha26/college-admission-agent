/**
 * api/client.js
 * Axios wrapper for the College Admission Agent backend.
 *
 * Uses POST /api/ask which returns:
 *   { answer: string, sources: [{ document: string, page: number }] }
 */

import axios from "axios";

// Base URL is handled by the Vite proxy in development (/api → localhost:8000).
// In production set VITE_API_BASE_URL in your environment.
const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  headers: { "Content-Type": "application/json" },
  timeout: 60_000, // 60 s — Granite can be slow on the first call
});

/**
 * Send a question to the RAG pipeline.
 *
 * @param {string} question  The user's question text.
 * @returns {Promise<{ answer: string, sources: Array<{ document: string, page: number }> }>}
 */
export async function sendMessage(question) {
  const { data } = await http.post("/api/ask", { question });
  return data;
}

/**
 * Check course eligibility against the RAG knowledge base.
 *
 * @param {{
 *   percentage_12th: number,
 *   maths_marks: number,
 *   physics_marks: number,
 *   chemistry_marks: number,
 *   preferred_course: string,
 * }} params
 * @returns {Promise<{
 *   analysis: string,
 *   disclaimer: string,
 *   sources: Array<{ document: string, page: number }>,
 * }>}
 */
export async function checkEligibility(params) {
  const { data } = await http.post("/api/eligibility", params);
  return data;
}
