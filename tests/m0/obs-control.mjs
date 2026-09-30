import { createHash } from "node:crypto";
import fs from "node:fs";
const cfg = JSON.parse(
  fs.readFileSync(
    new URL("../../runtime/m0/controller.json", import.meta.url),
    "utf8",
  ),
);
const ws = new WebSocket("ws://127.0.0.1:19445");
const pending = new Map();
let counter = 0;
const ready = new Promise((resolve, reject) => {
  ws.addEventListener("error", () =>
    reject(new Error("OBS websocket connection failed")),
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
            authentication: sha(sha(cfg.password + a.salt) + a.challenge),
          },
        }),
      );
    }
    if (msg.op === 2) resolve();
    if (msg.op === 7) {
      const p = pending.get(msg.d.requestId);
      if (p) {
        pending.delete(msg.d.requestId);
        if (msg.d.requestStatus.result) p.resolve(msg.d.responseData);
        else
          p.reject(
            new Error(msg.d.requestType + ": " + msg.d.requestStatus.comment),
          );
      }
    }
  });
});
function request(requestType, requestData = {}) {
  return new Promise((resolve, reject) => {
    const requestId = String(++counter);
    pending.set(requestId, { resolve, reject });
    ws.send(
      JSON.stringify({ op: 6, d: { requestType, requestId, requestData } }),
    );
  });
}
const timeout = setTimeout(() => {
  console.error("OBS setup timed out");
  process.exit(1);
}, 30000);
try {
  await ready;
  const version = await request("GetVersion");
  let { currentProgramSceneName: scene } = await request("GetSceneList");
  const inputDefinitions = [
    [
      "Pattern",
      "ffmpeg_source",
      { local_file: cfg.video, is_local_file: true, looping: true },
    ],
    [
      "Live440",
      "ffmpeg_source",
      { local_file: cfg.live, is_local_file: true, looping: true },
    ],
    [
      "Vod880",
      "ffmpeg_source",
      { local_file: cfg.vod, is_local_file: true, looping: true },
    ],
  ];
  // Inputs are independent; creation must precede track assignment for each input.
  await Promise.all(
    inputDefinitions.map(async ([name, kind, settings]) => {
      await request("CreateInput", {
        sceneName: scene,
        inputName: name,
        inputKind: kind,
        inputSettings: settings,
        sceneItemEnabled: true,
      });
      await request("SetInputAudioTracks", {
        inputName: name,
        inputAudioTracks: {
          1: name === "Live440",
          2: name === "Vod880",
          3: false,
          4: false,
          5: false,
          6: false,
        },
      });
    }),
  );
  await request("SetStreamServiceSettings", {
    streamServiceType: "rtmp_custom",
    streamServiceSettings: {
      server: "rtmp://127.0.0.1:19350/a",
      key: "obs?user=publisher&pass=" + encodeURIComponent(cfg.publishPassword),
      use_auth: false,
    },
  });
  await request("StartStream");
  await new Promise((r) => setTimeout(r, 2500));
  const status = await request("GetStreamStatus");
  if (!status.outputActive || status.outputBytes <= 0)
    throw new Error("OBS did not publish media");
  console.log(
    JSON.stringify({
      obsVersion: version.obsVersion,
      websocketVersion: version.obsWebSocketVersion,
      active: status.outputActive,
      bytes: status.outputBytes,
    }),
  );
} finally {
  clearTimeout(timeout);
  ws.close();
}
