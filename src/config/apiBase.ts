const PRODUCTION_API = "https://agrisentinel-api-va3i.onrender.com";

export const API_V1_PREFIX = "/api/v1";

export function resolveBackendRoot(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim() || import.meta.env.VITE_API_URL?.trim();
  // If configured with old URL without -va3i, ignore it and use correct PRODUCTION_API
  if (configured && configured.includes("agrisentinel-api-va3i.onrender.com")) {
    return configured.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
  }
  if (typeof window !== "undefined" && (window.location.hostname.includes("vercel.app") || window.location.hostname !== "localhost")) {
    return PRODUCTION_API;
  }
  if (configured) {
    return configured.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
  }
  return "http://localhost:8000";
}

export function resolveApiBase(): string {
  const root = resolveBackendRoot();
  return `${root}${API_V1_PREFIX}`;
}

export function resolveHealthCheckUrl(): string {
  const root = resolveBackendRoot();
  return `${root}/health`;
}
