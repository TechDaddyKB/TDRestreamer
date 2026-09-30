# M0 local dual-canvas media qualification

This standalone fixture exercises actual OBS multi-canvas encoding and the
proposed transport/copy-publisher path. Its custom encoder configuration is a
synthetic local fixture, **not a Twitch negotiation response**. Twitch delivery,
platform audio roles and application integration remain separate gates.

## Reproduction

The current runner targets Linux amd64 with OBS plugins in `/usr/lib/obs-plugins`
and plugin data in `/usr/share/obs/obs-plugins` (the tested Arch package layout).
Other filesystem layouts require a reviewed runner change, not silent skipping.
It requires OBS 32.2.2, obs-websocket 5.7.4, FFmpeg 9.0.1, Node with native
WebSocket support, Xvfb, bubblewrap, iproute2, Python 3, and a Fontconfig font for
fixture labels. Install the checksum-pinned MediaMTX binary as described in
[the original local harness](m0-local.md). User/network and bubblewrap mount
namespaces must work; X display `:199` must be free.

Stage Aitum Vertical 1.6.4 from its [official release](https://github.com/Aitum/obs-vertical-canvas/releases/tag/1.6.4)
without installing it into the user's OBS profile or system plugins:

```bash
set -euo pipefail
mkdir -p .tools/aitum-vertical/extracted .tools/aitum-vertical/data
curl -fL https://github.com/Aitum/obs-vertical-canvas/releases/download/1.6.4/vertical-canvas-linux-gnu.deb \
  -o .tools/aitum-vertical/plugin.deb
echo 'c982d6acf248f83e7e97d354055e245fa6957b66715f4249b849d913042aaf37  .tools/aitum-vertical/plugin.deb' | sha256sum -c -
ar p .tools/aitum-vertical/plugin.deb data.tar.gz | tar -xz -C .tools/aitum-vertical/extracted
install -m644 .tools/aitum-vertical/extracted/usr/lib/x86_64-linux-gnu/obs-plugins/vertical-canvas.so \
  .tools/aitum-vertical/vertical-canvas.so
cp -a .tools/aitum-vertical/extracted/usr/share/obs/obs-plugins/vertical-canvas/. .tools/aitum-vertical/data/
PYTHONOPTIMIZE=1 make m0-dual
```

The runner additionally enforces the extracted library SHA-256
`484c9663d00f3a2c2322600e6178833b7edde71019c2537b6eb35cf81e71e346`.
No network download occurs inside the test. The fixture refuses a namespace with
non-loopback interfaces or IPv4/IPv6 routes. OBS gets a fresh profile, software GL,
no microphone/camera/screen sources, and a private mount view containing only
the enumerated media plugins plus the pinned Aitum library. Backtrack and matching
the main output's recording/streaming state are disabled in Aitum's fixture config.
No plugin is installed or removed from the host. Fixture RTMP/RTSP sinks are
anonymous loopback services in that isolated network; this does not replace the
separate authenticated transport and tenant-denial qualification.

## Assertions and artifacts

- OBS encodes a labeled red 640×360 horizontal source and a labeled blue 360×640
  vertical source, each at 30 fps, into two H.264 tracks. The vertical canvas is
  1080×1920 and is scaled by the specified encoder configuration.
- Independent supplied audio sources contain 440 Hz and 880 Hz tones, assigned
  only to audio mixers 1 and 2 respectively; both are encoded as AAC.
- Read OBS ingest through MediaMTX's RTSP output. Require exactly two video and
  two audio tracks, correct codec/order/dimensions, ten decoded color samples per
  video, and expected audio frequency power over 100 times the opposite tone.
- Copy all four tracks through FFmpeg into enhanced RTMP, then repeat the same
  decoded identity and ordering checks at the receiving gateway.
- Negative unit controls reject swapped video identities/orientations, black or
  truncated samples, and missing audio. They run in `make unit`; the real media
  fixture is an explicitly configured local target, not an implicitly skipped CI job.

Each attempt writes a private `runtime/m0-dual-<random>/report.json` with status,
tool versions, source/module hashes, observations and limitations. Reports from
failed runs retain failure status; logs and generated WebSocket credentials stay
ignored and private. Processes are terminated on success, failure and command
timeout. Preserve the emitted report unchanged after scanning it before publication.

The [recorded run](m0-dual-canvas.json) is the successful emitted result. Its scope
is two low-resolution video tracks and two audio tracks in this local chain.
The color samples establish stream identity, not OCR, motion, frame timing,
A/V synchronization, latency, higher rendition ladders, GPU capacity, or soaks.
The configuration exercises OBS's real multitrack path but cannot establish
Twitch's accepted encoder configuration, wire-purpose metadata, viewer H/V
association or live/VOD playback. Follow the [Twitch procedure](m0-twitch-qualification.md)
for those remaining requirements and the separate broadcast approval boundary.
