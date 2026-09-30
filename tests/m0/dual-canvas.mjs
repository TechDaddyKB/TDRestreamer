import { obsConnection } from "./obs-rpc.mjs";
import fs from "node:fs";
import path from "node:path";

const obsControl = process.argv[2] === "--obs-control";
const runId = process.argv[obsControl ? 3 : 2];
if (!/^[a-f0-9]{12}$/.test(runId ?? ""))
  throw new Error("Invalid fixture run ID");
const runtimeRoot = obsControl
  ? "/dev/shm"
  : fs.realpathSync(new URL("../../runtime/", import.meta.url));
const expectedConfig = path.join(
  runtimeRoot,
  (obsControl ? "tdrestreamer-obs-control-" : "m0-dual-") + runId,
  "controller.json",
);
const configPath = fs.realpathSync(expectedConfig);
if (configPath !== expectedConfig)
  throw new Error("Symlinked fixture configuration refused");
const cfg = JSON.parse(fs.readFileSync(configPath, "utf8"));
if (!["rtmp://127.0.0.1:19350/dual", "rtmp://127.0.0.1:19351/dual",
      "rtmps://ingest.global-contribute.live-video.net/app"].includes(cfg.server) ||
    (obsControl !== (cfg.server === "rtmps://ingest.global-contribute.live-video.net/app")))
  throw new Error("Unexpected local OBS destination");
const { ready, request, close } = obsConnection(
  "ws://127.0.0.1:19447",
  obsControl ? process.env.M0_OBS_WS_PASSWORD : cfg.password,
);
const timeout = setTimeout(() => {
  console.error("Dual-canvas setup timed out");
  process.exit(1);
}, 45000);
try {
  await ready;
  const version = await request("GetVersion");
  const { canvases } = await request("GetCanvasList");
  const main = canvases.find((c) => c.canvasFlags.MAIN);
  const vertical = canvases.find((c) => c.canvasName === "Aitum Vertical");
  if (canvases.length !== 2 || !main || !vertical)
    throw new Error("Expected two canvases");
  await request("SetProfileParameter", {
    parameterCategory: "Stream1",
    parameterName: "MultitrackExtraCanvas",
    parameterValue: vertical.canvasUuid,
  });
  await Promise.all(
    [
      [main, "Horizontal", cfg.horizontal],
      [vertical, "Vertical", cfg.vertical],
    ].map(async ([canvas, name, file]) => {
      const sceneList = await request("GetSceneList", {
        canvasUuid: canvas.canvasUuid,
      });
      if (sceneList.scenes.length !== 1)
        throw new Error("Expected one fixture scene per canvas");
      const sceneName = sceneList.scenes[0].sceneName;
      const { sceneItemId } = await request("CreateInput", {
        canvasUuid: canvas.canvasUuid,
        sceneName,
        inputName: name,
        inputKind: "ffmpeg_source",
        inputSettings: { local_file: file, is_local_file: true, looping: true },
        sceneItemEnabled: true,
      });
      const width = name === "Horizontal" ? 640 : 360;
      const height = name === "Horizontal" ? 360 : 640;
      await request("SetSceneItemTransform", {
        canvasUuid: canvas.canvasUuid,
        sceneName,
        sceneItemId,
        sceneItemTransform: {
          positionX: 0,
          positionY: 0,
          scaleX: canvas.canvasVideoSettings.baseWidth / width,
          scaleY: canvas.canvasVideoSettings.baseHeight / height,
        },
      });
    }),
  );
  const { currentProgramSceneName: sceneName } = await request("GetSceneList", {
    canvasUuid: main.canvasUuid,
  });
  await Promise.all(
    [
      ["Live440", cfg.live, 1],
      ["Vod880", cfg.vod, 2],
    ].map(async ([name, file, track]) => {
      await request("CreateInput", {
        canvasUuid: main.canvasUuid,
        sceneName,
        inputName: name,
        inputKind: "ffmpeg_source",
        inputSettings: { local_file: file, is_local_file: true, looping: true },
        sceneItemEnabled: true,
      });
      await request("SetInputAudioTracks", {
        inputName: name,
        inputAudioTracks: Object.fromEntries(
          [1, 2, 3, 4, 5, 6].map((i) => [i, i === track]),
        ),
      });
    }),
  );
  await request("SetStreamServiceSettings", {
    streamServiceType: "rtmp_custom",
    streamServiceSettings: {
      server: cfg.server,
      key: "obs",
      use_auth: false,
    },
  });
  await request("StartStream");
  await new Promise((resolve) => setTimeout(resolve, 3000));
  const status = await request("GetStreamStatus");
  if (!status.outputActive || status.outputBytes <= 0)
    throw new Error("No OBS media");
  console.log(
    JSON.stringify({
      obsVersion: version.obsVersion,
      websocketVersion: version.obsWebSocketVersion,
      canvases: canvases.map((c) => ({
        name: c.canvasName,
        video: c.canvasVideoSettings,
      })),
      bytes: status.outputBytes,
    }),
  );
} finally {
  clearTimeout(timeout);
  close();
}
