# M0 local OBS and preview qualification

This is a feasibility harness, separate from the application's unfinished media
execution path. It uses real OBS, FFmpeg, MediaMTX and Chromium. It does not certify
M0 as complete or establish platform account eligibility.

The [recorded successful run](m0-obs-preview.json) passed OBS ingest, both decoded
audio identities after enhanced-RTMP relay, authenticated WebRTC, forced HLS
fallback, fresh-client access denials, RTMPS and encrypted-SRT preservation.

## Reproduce

On Linux install OBS Studio 32.2.2 with its bundled obs-websocket 5.7.4 plugin,
FFmpeg 9.0.1, Xvfb, Node and Python 3. Install the locked browser dependencies with
`make setup` and `cd web && npx playwright install chromium`. Put the
checksum-verified MediaMTX 1.21.1 release binary at `.tools/mediamtx/mediamtx`.
The Linux amd64 MediaMTX binary checksum and all tool versions are enforced by
[the toolchain manifest](../../tests/m0/toolchain.json). Run `make m0` from the project root. Unprivileged user/network namespaces and
creation of a dummy network interface must be available. This is an explicitly
configured local qualification target, not a silently skipped CI test.

The test enters a fresh network namespace, checks that it has no routes, enables
loopback and adds an unconnected dummy interface for Chromium ICE candidates.
There is no physical interface, veth, external default route or STUN server.
The host desktop and OBS profile are not used: OBS runs on a separate Xvfb display
with generated configuration, software rendering and synthetic media only.
The fixed X display `:197` must be free. No hardware capture source is configured.

Artifacts, logs, generated credentials and synthetic media stay under ignored
`runtime/m0`, accessible only to the current user. Do not publish that directory.
The report contains no passwords. Inspect its overall status and each test;
a failed command is a failed run, even if some preceding checks passed.
The processes are terminated on completion/failure, including command timeout.

## Assertions

- OBS publishes H.264 plus distinct live/VOD AAC tracks using custom RTMP and
  MediaMTX's query-credential convention. OBS's optional custom-server VOD track
  setting is enabled explicitly; this is not proof of Twitch behavior.
- Internal RTSP preserves both supplied tracks. Decoded PCM at each track index
  must contain the expected 440/880 Hz tone at over 100 times the opposite tone's
  spectral power.
- An FFmpeg publisher copies all tracks into enhanced RTMP; the receiving gateway
  must preserve both tracks and their decoded identities.
- Independent preview renditions copy video and select the first audio track.
  WebRTC converts selected AAC to Opus; HLS uses AAC. Chromium must decode more
  than 30 video frames, not merely fetch a playlist or accept signaling.
- An injected WHEP connection failure invokes HLS fallback and decoded frames
  must resume through HLS.
- Fresh clients with no credential, a different tenant's credential, or a denied
  credential must receive 401/403 for playlists, observed init/media fragments
  and WHEP. Query session credentials and cookies are removed for these checks.

- RTMPS verifies the generated test certificate and preserves both tracks.
  TLS rejects an untrusted certificate and a wrong hostname. Encrypted SRT
  preserves both tracks and rejects missing/wrong passphrases and wrong-tenant
  publishing. These secure-transport publishers use FFmpeg with OBS-origin media;
  native OBS RTMPS/SRT configuration itself is not certified.
- Qualification guards remain active with `PYTHONOPTIMIZE=1`; the recorded run
  uses that setting. Three guard regression tests run in `make unit` and CI.
  The report records hashes of its producing scripts and the browser version,
  and is copied unedited from the successful run.

## Authentication finding

MediaMTX 1.21.1 creates HLS sessions after initial authentication. Subsequent
requests can authenticate through a partitioned cookie or URL session parameter.
Reusing an authenticated browser's request context therefore does not test an
anonymous client. The harness uses independent clients without those credentials.
See the pinned [HLS server implementation](https://github.com/bluenviron/mediamtx/blob/v1.21.1/internal/servers/hls/http_server.go).

This test does not prove revocation of an already established HLS/WebRTC session,
application token expiry, or tenant enforcement in the production control plane.
Those require an application authorization boundary and explicit session lifetime
handling. Never expose session-bearing URLs in logs or share them as public links.

## Remaining gates

Actual Twitch Enhanced Broadcasting horizontal/vertical delivery, Twitch live/VOD
semantics remain unverified and require separate broadcast approval. Since this
local run, the owner authorized eligibility checks; the [account eligibility record](m0-account-eligibility.md)
documents platform dashboard and AWS read access, with application OAuth/API and
provider lifecycle capabilities still unverified. Additional OBS video/input
modes still need qualification in later media milestones. Browser audio
is negotiated but only server-side decoded audio identity is measured here;
preview latency, A/V synchronization, packet-loss behavior and long soaks are not
established by this short test. These limitations do not remove v1 requirements.
