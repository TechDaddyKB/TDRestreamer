import fs from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";
const require = createRequire(
  new URL("../../web/package.json", import.meta.url),
);
const { chromium, request } = require("@playwright/test");
const cfg = JSON.parse(
  fs.readFileSync(
    new URL("../../runtime/m0/controller.json", import.meta.url),
    "utf8",
  ),
);
const server = http.createServer((req, res) => {
  if (req.url === "/hls.js") {
    res.setHeader("Content-Type", "application/javascript");
    res.end(fs.readFileSync(require.resolve("hls.js/dist/hls.min.js")));
    return;
  }
  res.setHeader("Content-Type", "text/html");
  res.end(
    "<!doctype html><title>M0 preview lab</title><video muted autoplay playsinline></video>",
  );
});
await new Promise((r) => server.listen(18090, "127.0.0.1", r));
const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"],
});
const results = { browserVersion: browser.version() };
let diagnosticPage;
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  diagnosticPage = page;
  await page.goto("http://127.0.0.1:18090");
  await page.addScriptTag({ url: "http://127.0.0.1:18889/a/webrtc/reader.js" });
  await page.evaluate(
    ({ password }) => {
      window.errors = [];
      window.pcs = [];
      const OriginalPC = window.RTCPeerConnection;
      window.RTCPeerConnection = class extends OriginalPC {
        constructor(...args) {
          super(...args);
          window.pcs.push(this);
        }
      };
      window.reader = new window.MediaMTXWebRTCReader({
        url: "http://127.0.0.1:18889/a/webrtc/whep",
        user: "reader-a",
        pass: password,
        onError: (e) => window.errors.push(e),
        onTrack: (e) => {
          document.querySelector("video").srcObject = e.streams[0];
        },
      });
    },
    { password: cfg.readerPassword },
  );
  await page.waitForFunction(
    () =>
      document.querySelector("video").getVideoPlaybackQuality()
        .totalVideoFrames > 30,
    null,
    { timeout: 20000 },
  );
  results.webrtc = await page.evaluate(() => ({
    frames: document.querySelector("video").getVideoPlaybackQuality()
      .totalVideoFrames,
    time: document.querySelector("video").currentTime,
    tracks: document
      .querySelector("video")
      .srcObject.getTracks()
      .map((t) => t.kind),
    errors: window.errors,
  }));
  await page.evaluate(() => window.reader.close());
  await page.goto("http://127.0.0.1:18090");
  await page.addScriptTag({ url: "http://127.0.0.1:18090/hls.js" });
  await page.addScriptTag({ url: "http://127.0.0.1:18889/a/webrtc/reader.js" });
  await page.route("**/whep", (route) => route.abort("connectionrefused"));
  const mediaURLs = new Set();
  page.on("response", (r) => {
    if (r.url().startsWith("http://127.0.0.1:18888/") && r.ok())
      mediaURLs.add(r.url());
  });
  await page.evaluate(
    ({ password }) => {
      window.fallbackTriggered = false;
      window.fallbackReader = new MediaMTXWebRTCReader({
        url: "http://127.0.0.1:18889/a/webrtc/whep",
        user: "reader-a",
        pass: password,
        onError: () => {
          if (window.fallbackTriggered) return;
          window.fallbackTriggered = true;
          window.fallbackReader.close();
          window.hls = new Hls({
            xhrSetup: (x) =>
              x.setRequestHeader(
                "Authorization",
                "Basic " + btoa("reader-a:" + password),
              ),
          });
          window.hls.loadSource("http://127.0.0.1:18888/a/hls/index.m3u8");
          window.hls.attachMedia(document.querySelector("video"));
        },
      });
    },
    { password: cfg.readerPassword },
  );
  await page.waitForFunction(
    () =>
      document.querySelector("video").getVideoPlaybackQuality()
        .totalVideoFrames > 30,
    null,
    { timeout: 30000 },
  );
  results.hls = await page.evaluate(() => ({
    fallbackTriggered: window.fallbackTriggered,
    frames: document.querySelector("video").getVideoPlaybackQuality()
      .totalVideoFrames,
    time: document.querySelector("video").currentTime,
  }));
  if (!results.hls.fallbackTriggered)
    throw new Error("HLS fallback was not exercised");
  if (![...mediaURLs].some((x) => x.includes(".mp4")))
    throw new Error("No HLS fragment decoded");
  // Freeze the observed resource set before testing independent unauthorized clients.
  await page.evaluate(() => window.hls.destroy());
  const observedMediaURLs = Array.from(mediaURLs);
  const denialResults = await Promise.all(
    [
      ["anonymous", null],
      ["reader-b", cfg.otherPassword],
      ["expired", cfg.expiredPassword],
    ].map(async ([identity, password]) => {
      const headers = password
        ? {
            Authorization:
              "Basic " +
              Buffer.from(identity + ":" + password).toString("base64"),
          }
        : {};
      const client = await request.newContext();
      try {
        const resources = await Promise.all(
          observedMediaURLs.map(async (credentialedURL) => {
            const url = new URL(credentialedURL);
            url.search = "";
            const response = await client.get(url.href, { headers });
            if (![401, 403].includes(response.status()))
              throw new Error(
                "HLS unauthorized request accepted: " + response.status(),
              );
            return { identity, path: url.pathname, status: response.status() };
          }),
        );
        const response = await client.post(
          "http://127.0.0.1:18889/a/webrtc/whep",
          {
            headers: { ...headers, "Content-Type": "application/sdp" },
            data: "v=0\r\n",
          },
        );
        if (![401, 403].includes(response.status()))
          throw new Error(
            "WHEP unauthorized request accepted: " + response.status(),
          );
        return [
          ...resources,
          { identity, path: "/a/webrtc/whep", status: response.status() },
        ];
      } finally {
        await client.dispose();
      }
    }),
  );
  results.access_denials = denialResults.flat();
  console.log(JSON.stringify(results));
} catch (error) {
  console.error(
    JSON.stringify({
      partial: results,
      browser: await diagnosticPage?.evaluate(() => ({
        errors: window.errors,
        pcs: window.pcs?.map((p) => ({
          connection: p.connectionState,
          ice: p.iceConnectionState,
          localCandidates:
            p.localDescription?.sdp.match(/a=candidate:/g)?.length,
          remoteCandidates:
            p.remoteDescription?.sdp.match(/a=candidate:/g)?.length,
        })),
        video: {
          ready: document.querySelector("video").readyState,
          time: document.querySelector("video").currentTime,
        },
      })),
    }),
  );
  throw error;
} finally {
  await browser.close();
  await new Promise((r) => server.close(r));
}
