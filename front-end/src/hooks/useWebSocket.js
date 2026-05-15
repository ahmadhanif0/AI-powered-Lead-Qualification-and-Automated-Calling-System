import { useState, useEffect, useRef } from "react";
import { WS_BASE } from "../api/client";

/**
 * Connects to the backend WebSocket at /ws.
 * Returns { events, wsStatus }
 * `events` is a capped array of the last 50 messages.
 */
export function useWebSocket(onMessage) {
  const [wsStatus, setWsStatus] = useState("disconnected");
  const [events,   setEvents]   = useState([]);
  const cbRef = useRef(onMessage);
  cbRef.current = onMessage;

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws`);

    ws.onopen    = () => setWsStatus("connected");
    ws.onerror   = () => setWsStatus("error");
    ws.onclose   = () => setWsStatus("disconnected");

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setEvents((prev) => [msg, ...prev].slice(0, 50));
      cbRef.current?.(msg);
    };

    return () => ws.close();
  }, []);

  return { events, wsStatus };
}
