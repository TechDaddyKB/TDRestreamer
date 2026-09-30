import type { components } from "./generated-api";
export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  body?: unknown,
  headers: Record<string, string> = {},
): Promise<T> {
  const res = await fetch("/api/v1" + path, {
    method: body === undefined ? "GET" : "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-TDR-Request": "1",
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok)
    throw new APIError(res.status, data.error?.message ?? "Request failed");
  return data as T;
}
export type Principal = components["schemas"]["Principal"];
export type Session = components["schemas"]["Session"];
export type Resource = {
  id: string;
  name: string;
  orientation?: string;
  platform?: string;
  credential_set: boolean;
};
export type Capabilities = {
  publishing: boolean;
  preview: boolean;
  remote_workers: boolean;
  cloud_provisioning: boolean;
};
