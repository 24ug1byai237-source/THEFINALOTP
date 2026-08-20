const PRODUCTION_API = "https://agrisentinel-api.onrender.com";

function resolveApiBase(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined" && window.location.hostname.includes("vercel.app")) {
    return PRODUCTION_API;
  }
  return "http://localhost:8000";
}

const API_BASE = resolveApiBase();

/** Resolve uploaded file URLs from API (handles relative paths, legacy localhost, and data URLs). */
export function resolveMediaUrl(url: string | undefined | null): string {
  if (!url) return "";
  const cleaned = url.trim();
  if (!cleaned || cleaned === "#") return "";

  if (cleaned.startsWith("data:")) return cleaned;

  if (cleaned.startsWith("http://localhost") || cleaned.startsWith("https://localhost")) {
    try {
      const path = new URL(cleaned).pathname;
      return `${API_BASE.replace(/\/$/, "")}${path}`;
    } catch {
      return cleaned;
    }
  }

  if (cleaned.startsWith("http://") || cleaned.startsWith("https://")) {
    return cleaned;
  }

  const path = cleaned.startsWith("/") ? cleaned : `/${cleaned}`;
  return `${API_BASE.replace(/\/$/, "")}${path}`;
}

export function isImageFile(nameOrUrl: string): boolean {
  return /\.(jpe?g|png|gif|webp|bmp)$/i.test(nameOrUrl.split("?")[0]);
}

export function isPdfFile(nameOrUrl: string): boolean {
  return /\.pdf$/i.test(nameOrUrl.split("?")[0]);
}

/**
 * The backend's /media/{fileId} endpoint now requires a Bearer token (it
 * used to be publicly readable by anyone who knew/guessed a file UUID).
 * A plain <img src="..."> or <a href="..."> navigation can't attach an
 * Authorization header, so evidence images/PDFs must be fetched here and
 * rendered via a local blob object URL instead of pointing straight at the
 * backend URL.
 *
 * Callers own the returned object URL and must revoke it (URL.revokeObjectURL)
 * once it's no longer needed, e.g. on unmount.
 */
export async function fetchMediaBlobUrl(url: string | undefined | null): Promise<string> {
  const resolved = resolveMediaUrl(url);
  if (!resolved) throw new Error("No media URL available");

  // Data URLs (e.g. cached-offline inline evidence) need no auth/fetching.
  if (resolved.startsWith("data:")) return resolved;

  const token = localStorage.getItem("accessToken");
  const response = await fetch(resolved, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new Error(`Failed to load media (${response.status})`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
