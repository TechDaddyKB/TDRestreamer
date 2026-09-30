// Read-only M0 account preflight. Credentials and the short-lived token stay in memory.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const lookup = (kind) =>
  execFileSync(
    "secret-tool",
    [
      "lookup",
      "service",
      "tdrestreamer",
      "account",
      "twitch-m0",
      "kind",
      kind,
    ],
    { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
  ).trim();

const report = {
  observedAt: new Date().toISOString(),
  node: process.version,
  harnessSha256: createHash("sha256")
    .update(readFileSync(new URL(import.meta.url)))
    .digest("hex"),
  credentialSource: "local Secret Service keyring",
  tokenStatus: null,
  tokenObtained: false,
  usersStatus: null,
  userCount: null,
  loginMatches: false,
};

try {
  const clientId = lookup("client-id");
  const clientSecret = lookup("client-secret");
  if (!/^[A-Za-z0-9]{20,}$/.test(clientId) ||
      !/^[A-Za-z0-9_-]{20,}$/.test(clientSecret)) {
    throw new Error("credential_shape");
  }

  const tokenResponse = await fetch("https://id.twitch.tv/oauth2/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: "client_credentials",
    }),
    signal: AbortSignal.timeout(15_000),
  });
  report.tokenStatus = tokenResponse.status;
  if (!tokenResponse.ok) throw new Error("token_http");
  const tokenBody = await tokenResponse.json();
  if (typeof tokenBody.access_token !== "string" ||
      tokenBody.token_type !== "bearer") {
    throw new Error("token_shape");
  }
  report.tokenObtained = true;
  report.tokenType = tokenBody.token_type;
  report.tokenExpiresInSeconds = tokenBody.expires_in;

  const usersResponse = await fetch(
    "https://api.twitch.tv/helix/users?login=TechDaddy",
    {
      headers: {
        "Client-Id": clientId,
        Authorization: `Bearer ${tokenBody.access_token}`,
      },
      signal: AbortSignal.timeout(15_000),
    },
  );
  report.usersStatus = usersResponse.status;
  if (!usersResponse.ok) throw new Error("users_http");
  const usersBody = await usersResponse.json();
  report.userCount = Array.isArray(usersBody.data) ? usersBody.data.length : null;
  report.loginMatches =
    Array.isArray(usersBody.data) &&
    usersBody.data.some(
      (user) => String(user.login).toLowerCase() === "techdaddy",
    );
  if (!report.loginMatches) throw new Error("user_mismatch");
} catch (error) {
  // Never print fetch errors, response bodies, credentials, or token values.
  report.failure =
    error instanceof Error &&
    ["credential_shape", "token_http", "token_shape", "users_http", "user_mismatch"].includes(error.message)
      ? error.message
      : "preflight_error";
  process.exitCode = 1;
}

console.log(JSON.stringify(report));
