const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

/**
 * Returns the signed-in user's access token, or null when running locally
 * (the backend treats every request as the local user). When the app moves to
 * AWS, wire this to Cognito (e.g. Amplify's fetchAuthSession).
 */
let tokenProvider: () => Promise<string | null> = async () => null;

export function setTokenProvider(provider: () => Promise<string | null>) {
  tokenProvider = provider;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Params = Record<string, string | number | null | undefined>;

function buildUrl(path: string, params?: Params): string {
  const url = `${BASE_URL}/api${path}`;
  if (!params) return url;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `${url}?${qs}` : url;
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      // Validation errors: name the field, e.g. "default_range: Extra inputs are not permitted".
      return body.detail
        .map((d: { msg: string; loc?: (string | number)[] }) => {
          const field = d.loc?.[d.loc.length - 1];
          return typeof field === "string" && field !== "body" ? `${field}: ${d.msg}` : d.msg;
        })
        .join("; ");
    }
  } catch {
    // fall through
  }
  return `${res.status} ${res.statusText}`;
}

export async function request<T>(
  method: string,
  path: string,
  options: { params?: Params; json?: unknown; form?: FormData } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = await tokenProvider();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    body = options.form;
  }
  const res = await fetch(buildUrl(path, options.params), { method, headers, body });
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>("GET", path, { params }),
  post: <T>(path: string, json?: unknown) => request<T>("POST", path, { json }),
  patch: <T>(path: string, json: unknown) => request<T>("PATCH", path, { json }),
  del: (path: string) => request<void>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, { form }),
};
