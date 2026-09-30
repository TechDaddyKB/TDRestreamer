import { useEffect, useState } from "react";
type Operation = { summary: string; requestBody?: unknown; responses: unknown };
type Schema = {
  info: { title: string; description: string };
  paths: Record<string, Record<string, Operation>>;
};
export default function Docs() {
  const [schema, setSchema] = useState<Schema | null>(null),
    [error, setError] = useState(""),
    [result, setResult] = useState("");
  useEffect(() => {
    fetch("/api/v1/openapi.json")
      .then((r) => {
        if (!r.ok) throw new Error("API schema unavailable");
        return r.json();
      })
      .then(setSchema)
      .catch((e) => setError(e.message));
  }, []);
  async function inspect(path: string) {
    try {
      const res = await fetch(path);
      setResult(JSON.stringify(await res.json(), null, 2));
    } catch {
      setResult("Request failed");
    }
  }
  if (error) return <p role="alert">{error}</p>;
  if (!schema) return <p>Loading schema…</p>;
  return (
    <>
      <h2>REST API reference</h2>
      <p>{schema.info.description}</p>
      <p>
        <a href="/api/v1/openapi.json" download>
          Download OpenAPI 3.1 JSON
        </a>
      </p>
      <p>
        Mutations require X-TDR-Request: 1. Session actions also require
        Idempotency-Key and an expected revision. Authentication uses the
        current same-origin session.
      </p>
      {Object.entries(schema.paths).flatMap(([path, methods]) =>
        Object.entries(methods).map(([method, op]) => (
          <details key={method + path}>
            <summary>
              <b>{method.toUpperCase()}</b> <code>{path}</code> — {op.summary}
            </summary>
            <pre>{JSON.stringify(op, null, 2)}</pre>
            {method === "get" &&
              !path.includes("{") &&
              !path.endsWith("/events") && (
                <button onClick={() => void inspect(path)}>
                  Send read-only request
                </button>
              )}
          </details>
        )),
      )}
      {result && (
        <section>
          <h3>Response</h3>
          <pre>{result}</pre>
        </section>
      )}
    </>
  );
}
