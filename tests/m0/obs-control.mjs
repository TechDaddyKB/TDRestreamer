import { obsConnection } from "./obs-rpc.mjs";
import fs from "node:fs";
const cfg = JSON.parse(
  fs.readFileSync(
    new URL("../../runtime/m0/controller.json", import.meta.url),
    "utf8",
  ),
);
const { ready, request, close } = obsConnection(
  "ws://127.0.0.1:19445",
  cfg.password,
);
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
  close();
}
