async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (res.status === 401 && path !== "/api/auth/login") {
    try {
      const r = await fetch("/api/auth/refresh", { method: "POST", credentials: "include" });
      if (r.ok) {
        const retry = await fetch(path, {
          credentials: "include",
          headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
          ...init,
        });
        if (!retry.ok) throw await asError(retry);
        return retry.status === 204 ? (undefined as T) : ((await retry.json()) as T);
      }
    } catch {
      /* fall through */
    }
    if (
      path !== "/api/auth/me" &&
      path !== "/api/auth/refresh" &&
      window.location.pathname !== "/login"
    ) {
      window.location.href = "/login";
    }
    throw new Error("unauthenticated");
  }
  if (!res.ok) throw await asError(res);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

async function asError(res: Response): Promise<Error> {
  let msg = `${res.status} ${res.statusText}`;
  try {
    const body = await res.json();
    if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {}
  const e = new Error(msg);
  (e as any).status = res.status;
  return e;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) => request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(p: string, body?: unknown) => request<T>(p, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(p: string, body?: unknown) => request<T>(p, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(p: string) => request<T>(p, { method: "DELETE" }),
};
