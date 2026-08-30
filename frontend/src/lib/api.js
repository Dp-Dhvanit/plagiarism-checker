/**
 * Thin fetch helpers. All calls go to same-origin paths that Vite proxies to
 * the FastAPI backend (see vite.config.js) — no API keys ever reach the
 * browser; Gemini is used server-side only.
 */

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** True when the request was cancelled by the caller (abort), not failed. */
export function isAbort(err) {
  return err?.name === "AbortError" || err?.name === "CanceledError";
}

async function handleResponse(res) {
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new ApiError(d.detail || `Request failed (${res.status})`, res.status);
  }
  return res.json();
}

function wrapNetworkError(err) {
  if (isAbort(err) || err instanceof ApiError) return err;
  return new ApiError(
    "Could not reach the analysis backend. Make sure it is running on port 8000.",
    0
  );
}

export async function postJSON(url, body, { signal } = {}) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
    return await handleResponse(res);
  } catch (err) {
    throw wrapNetworkError(err);
  }
}

export async function postForm(url, formData, { signal } = {}) {
  try {
    const res = await fetch(url, { method: "POST", body: formData, signal });
    return await handleResponse(res);
  } catch (err) {
    throw wrapNetworkError(err);
  }
}

export async function getJSON(url, { signal } = {}) {
  try {
    const res = await fetch(url, { signal });
    return await handleResponse(res);
  } catch (err) {
    throw wrapNetworkError(err);
  }
}

export async function deleteJSON(url, { signal } = {}) {
  try {
    const res = await fetch(url, { method: "DELETE", signal });
    return await handleResponse(res);
  } catch (err) {
    throw wrapNetworkError(err);
  }
}

export async function downloadFile(url, suggestedName) {
  let res;
  try {
    res = await fetch(url);
  } catch (err) {
    throw wrapNetworkError(err);
  }
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new ApiError(d.detail || `Could not generate the report (${res.status})`, res.status);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = suggestedName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}
