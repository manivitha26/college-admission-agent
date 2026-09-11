/**
 * hooks/useChat.js
 * Manages the full message history and the loading / error states.
 *
 * Returned values
 * ---------------
 * messages   – array of { id, role, text, sources, isError }
 * isLoading  – true while waiting for the backend
 * sendMessage(text) – appends the user turn, calls the API, appends AI turn
 */

import { useState, useCallback } from "react";
import { sendMessage as apiSend } from "../api/client";

// Every message in the list looks like this:
// {
//   id:       string,   — unique key for React's list rendering
//   role:     "user" | "assistant",
//   text:     string,
//   sources:  Array<{ document: string, page: number }>,
//   isError:  boolean,
// }

function makeId() {
  return Math.random().toString(36).slice(2);
}

export function useChat() {
  const [messages, setMessages]   = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    // 1. Append the user's message immediately so the UI feels responsive.
    const userMsg = {
      id:      makeId(),
      role:    "user",
      text:    trimmed,
      sources: [],
      isError: false,
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      // 2. Call POST /api/ask.
      const data = await apiSend(trimmed);

      // 3. Append the AI reply.
      const aiMsg = {
        id:      makeId(),
        role:    "assistant",
        text:    data.answer,
        sources: data.sources ?? [],
        isError: false,
      };
      setMessages((prev) => [...prev, aiMsg]);

    } catch (err) {
      // 4. On any error, append an error bubble instead of crashing.
      const detail =
        err?.response?.data?.detail ??
        err?.message ??
        "Something went wrong. Please try again.";

      const errMsg = {
        id:      makeId(),
        role:    "assistant",
        text:    detail,
        sources: [],
        isError: true,
      };
      setMessages((prev) => [...prev, errMsg]);

    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  return { messages, isLoading, sendMessage };
}
