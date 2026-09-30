import { obsConnection } from "./obs-rpc.mjs";
import fs from "node:fs";
import path from "node:path";

const runId = process.argv[2];
if (!/^[a-f0-9]{12}$/.test(runId ?? ""))
  throw new Error("Invalid control run ID");
const expected = path.join("/dev/shm", "tdrestreamer-obs-control-" + runId,
  "controller.json");
if (fs.realpathSync(expected) !== expected)
  throw new Error("Symlinked control configuration refused");
const cfg = JSON.parse(fs.readFileSync(expected, "utf8"));
const { ready, request, close } = obsConnection("ws://127.0.0.1:19447", cfg.password);
const timeout = setTimeout(() => process.exit(1), 15000);
try {
  await ready;
  const before = await request("GetStreamStatus");
  if (before.outputActive)
    await request("StopStream");
  let after = await request("GetStreamStatus");
  const deadline = Date.now() + 10000;
  while (after.outputActive && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 250));
    after = await request("GetStreamStatus");
  }
  console.log(JSON.stringify({ active_before_stop: !!before.outputActive,
    active_after_stop: !!after.outputActive, bytes: before.outputBytes ?? 0 }));
} finally {
  clearTimeout(timeout);
  close();
}
