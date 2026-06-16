"use client";

import { useEffect, useRef, useState } from "react";
import { eventStreamUrl } from "./api";
import type { CloudEvent } from "./types";

// Subscribe to the live CloudEvents WebSocket. Calls onEvent for each event and
// reports connection status. One connection per mounted consumer.
export function useEventStream(onEvent?: (e: CloudEvent) => void) {
  const [connected, setConnected] = useState(false);
  const cb = useRef(onEvent);
  cb.current = onEvent;

  useEffect(() => {
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(eventStreamUrl());
    } catch {
      return;
    }
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (msg) => {
      try {
        cb.current?.(JSON.parse(msg.data) as CloudEvent);
      } catch {
        /* ignore malformed frames */
      }
    };
    return () => ws?.close();
  }, []);

  return { connected };
}
