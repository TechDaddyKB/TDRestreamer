import { createHash } from "node:crypto";

// OBS WebSocket v5 protocol authentication, not password-storage hashing.
// Callers generate a fresh 192-bit random fixture credential per isolated run.
export function obsConnection(url, password) {
  const ws = new WebSocket(url);
  const pending = new Map();
  let counter = 0;
  const ready = new Promise((resolve, reject) => {
    ws.addEventListener("error", () =>
      reject(new Error("OBS connection failed")),
    );
    ws.addEventListener("message", ({ data }) => {
      const msg = JSON.parse(data);
      if (msg.op === 0) {
        const a = msg.d.authentication;
        const sha = (x) => createHash("sha256").update(x).digest("base64");
        ws.send(
          JSON.stringify({
            op: 1,
            d: {
              rpcVersion: 1,
              eventSubscriptions: 0,
              authentication: sha(sha(password + a.salt) + a.challenge),
            },
          }),
        );
      }
      if (msg.op === 2) resolve();
      if (msg.op === 7) {
        const p = pending.get(msg.d.requestId);
        if (!p) return;
        pending.delete(msg.d.requestId);
        if (msg.d.requestStatus.result) p.resolve(msg.d.responseData);
        else
          p.reject(
            new Error(msg.d.requestType + ": " + msg.d.requestStatus.comment),
          );
      }
    });
  });
  return {
    ready,
    request(requestType, requestData = {}) {
      return new Promise((resolve, reject) => {
        const requestId = String(++counter);
        pending.set(requestId, { resolve, reject });
        ws.send(
          JSON.stringify({ op: 6, d: { requestType, requestId, requestData } }),
        );
      });
    },
    close() {
      ws.close();
    },
  };
}
