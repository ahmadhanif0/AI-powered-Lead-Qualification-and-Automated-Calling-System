import { useEffect, useRef, useState } from "react";
import { Download, Mic, MicOff, Phone, X } from "lucide-react";
import { api }     from "../api/client";
import { Modal }   from "./Modal";
import { Spinner } from "./Spinner";

const POLL_INTERVAL_MS = 2500;   // poll every 2.5 s while call is active

// ── Call status helpers ───────────────────────────────────────────────
const ACTIVE_STATUSES = new Set(["calling", "in-progress", "in_progress", "queued"]);

function isActive(status) {
  return ACTIVE_STATUSES.has((status || "").toLowerCase());
}

function isCompleted(status) {
  const s = (status || "").toLowerCase();
  return s === "completed" || s === "call_not_attended" || s === "call_rejected" || s === "wrong_number";
}

// ── Message bubble ────────────────────────────────────────────────────
function Bubble({ role, text }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-2`}>
      <div
        className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white font-semibold rounded-br-sm"
            : "bg-gray-700 text-gray-100 font-normal rounded-bl-sm"
        }`}
      >
        <span className="block text-[10px] mb-1 opacity-60 uppercase tracking-wide">
          {isUser ? "Lead" : "Assistant"}
        </span>
        {text}
      </div>
    </div>
  );
}

// ── LiveTranscriptModal ───────────────────────────────────────────────
/**
 * Props:
 *   lead        — { id, name, call_status }
 *   onClose     — () => void
 */
export function LiveTranscriptModal({ lead, onClose }) {
  const [data,    setData]    = useState(null);   // { transcript, call_status, recording_url, ... }
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const bottomRef  = useRef(null);
  const intervalRef = useRef(null);

  // ── Fetch transcript ────────────────────────────────────────────────
  async function fetchTranscript() {
    try {
      const res = await api.calls.liveTranscript(lead.id);
      setData(res);
      setError(null);

      // Stop polling once the call is no longer active
      if (!isActive(res.call_status)) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Start polling on mount ──────────────────────────────────────────
  useEffect(() => {
    fetchTranscript();

    // Only poll if the call might still be active
    if (isActive(lead.call_status)) {
      intervalRef.current = setInterval(fetchTranscript, POLL_INTERVAL_MS);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [lead.id]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auto-scroll to bottom on new messages ──────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [data?.transcript?.length]);

  // ── Derived state ───────────────────────────────────────────────────
  const callStatus    = data?.call_status   || lead.call_status || "unknown";
  const recordingUrl  = data?.recording_url || null;
  const transcript    = data?.transcript    || [];
  const aiDecision    = data?.ai_decision   || null;
  const duration      = data?.duration_seconds;
  const active        = isActive(callStatus);
  const done          = isCompleted(callStatus);

  // ── Status badge ────────────────────────────────────────────────────
  function StatusBadge() {
    if (active) {
      return (
        <span className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-red-900/60 text-red-300 border border-red-700 animate-pulse">
          <Mic size={11} /> Recording in progress…
        </span>
      );
    }
    if (done) {
      return (
        <span className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-green-900/60 text-green-300 border border-green-700">
          <MicOff size={11} /> Call ended
          {duration ? ` · ${Math.round(duration)}s` : ""}
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-gray-700 text-gray-400">
        <Phone size={11} /> {callStatus}
      </span>
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Transcript — ${lead.name || `Lead #${lead.id}`}`}
      maxWidth="max-w-xl"
    >
      <div className="flex flex-col gap-3" style={{ minHeight: "360px" }}>

        {/* Status bar */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <StatusBadge />
          {aiDecision && (
            <span className="text-xs text-gray-400">
              AI Decision: <span className="text-white font-medium">{aiDecision}</span>
            </span>
          )}
        </div>

        {/* Transcript window */}
        <div className="flex-1 bg-gray-950 border border-gray-800 rounded-xl p-3 overflow-y-auto"
          style={{ maxHeight: "340px", minHeight: "200px" }}>

          {loading ? (
            <div className="flex justify-center items-center h-full py-8">
              <Spinner />
            </div>
          ) : error ? (
            <p className="text-red-400 text-xs text-center py-8">{error}</p>
          ) : transcript.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-8 gap-2 text-gray-600">
              <Mic size={24} />
              <p className="text-sm">
                {active
                  ? "Waiting for conversation to start…"
                  : "No transcript available for this call."}
              </p>
            </div>
          ) : (
            <>
              {transcript.map((msg, i) => (
                <Bubble key={i} role={msg.role} text={msg.text} />
              ))}
              {/* Live typing indicator while call is active */}
              {active && (
                <div className="flex justify-start mb-2">
                  <div className="bg-gray-700 rounded-2xl rounded-bl-sm px-4 py-2.5 flex gap-1 items-center">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {/* Audio player + footer actions */}
        <div className="flex flex-col gap-2 pt-1">

          {/* Inline audio player — only when call is done and recording URL exists */}
          {done && recordingUrl && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 space-y-1.5">
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
                Call Recording
              </p>
              <audio
                controls
                src={recordingUrl}
                style={{ width: "100%", height: "36px", accentColor: "#3b82f6" }}
                className="rounded"
              >
                Your browser does not support audio playback.
              </audio>
            </div>
          )}

          {/* Button row */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm transition-colors"
            >
              Close
            </button>

            {/* Download Recording — keep alongside the player */}
            {done && recordingUrl && (
              <a
                href={recordingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded bg-green-700 hover:bg-green-600 text-sm font-medium transition-colors"
              >
                <Download size={14} /> Download
              </a>
            )}

            {/* Refresh button while active */}
            {active && (
              <button
                onClick={fetchTranscript}
                className="flex items-center gap-1 px-3 py-2 rounded bg-gray-700 hover:bg-gray-600 text-xs text-gray-400 transition-colors"
              >
                Refresh
              </button>
            )}
          </div>
        </div>

        {/* Recording note when done but no URL */}
        {done && !recordingUrl && !loading && (
          <p className="text-xs text-gray-600 text-center -mt-1">
            No recording available — recording may be disabled for this assistant.
          </p>
        )}
      </div>
    </Modal>
  );
}
