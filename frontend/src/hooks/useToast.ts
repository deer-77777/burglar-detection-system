import { create } from "zustand";

export type ToastSeverity = "success" | "info" | "warning" | "error";

type Toast = {
  id: number;
  message: string;
  severity: ToastSeverity;
};

type ToastStore = {
  toasts: Toast[];
  push: (message: string, severity: ToastSeverity) => void;
  dismiss: (id: number) => void;
  success: (message: string) => void;
  info: (message: string) => void;
  error: (message: string) => void;
};

let nextId = 1;

export const useToast = create<ToastStore>((set, get) => ({
  toasts: [],
  push: (message, severity) =>
    set((s) => ({ toasts: [...s.toasts, { id: nextId++, message, severity }] })),
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  success: (m) => get().push(m, "success"),
  info: (m) => get().push(m, "info"),
  error: (m) => get().push(m, "error"),
}));
