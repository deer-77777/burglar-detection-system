import { useEffect, useState } from "react";

export type DashboardEvent = {
  channel: string;
  data: {
    event_id?: number;
    camera_id: number;
    event_type?: "DWELL" | "REVISIT";
    person_global_id?: string;
    start_time?: string;
    end_time?: string;
    duration_sec?: number | null;
    appearance_count?: number | null;
  };
};

export function useDashboardEvents() {
  const [last, setLast] = useState<DashboardEvent | null>(null);
  const [alertsByCam, setAlertsByCam] = useState<Record<number, number>>({});

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/dashboard`);
    ws.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data) as DashboardEvent;
        setLast(ev);
        if (ev.channel === "events:new") {
          setAlertsByCam((prev) => ({
            ...prev,
            [ev.data.camera_id]: (prev[ev.data.camera_id] ?? 0) + 1,
          }));
        }
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, []);

  return { last, alertsByCam };
}
