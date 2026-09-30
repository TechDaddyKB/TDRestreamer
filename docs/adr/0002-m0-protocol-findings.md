# ADR 0002: M0 protocol findings and conditional integration constraints

Status: recorded local feasibility findings, 2026-09-30. This supplements the
owner-approved architecture; it does not waive M0's unresolved external gates.

Retain pinned MediaMTX 1.21.1 and FFmpeg 9.0.1 for the next local development work.
Real OBS 32.2.2 supplied two separate AAC tracks over custom RTMP. Internal RTSP
and enhanced-RTMP publishing preserved their decoded identities. RTMPS with
certificate verification and encrypted SRT/MPEG-TS also preserved both tracks.
See [reproduction and evidence](../evidence/m0-local.md).

Use explicit enhanced-RTMP capabilities for the multi-audio FFmpeg copy path.
Do not assume ordinary RTMP packaging, multiple channels inside one audio track,
and separate supplied live/VOD tracks are interchangeable. The custom OBS VOD
track setting and MediaMTX query-credential convention are explicit fixture
requirements. Platform-specific live/VOD metadata still needs actual delivery
and VOD playback evidence.

Preview uses an independently selected track: AAC is converted to Opus for the
proven WebRTC path; the HLS path uses AAC. The browser must decode frames, not
merely accept a WHEP response or download a playlist. MediaMTX HLS session cookies
or URL credentials are authorization material. Application integration must
protect them, define session expiry/revocation and enforce tenant boundaries;
a local auth callback alone is not that implementation.

RunPod's documented lack of public UDP exposure constrains deployment topology.
Keep SRT on the agreed stable ingress edge and use an authenticated encrypted TCP
path to workers. Direct outward destination publishing remains worker-owned.
Preview edge/TCP relay design still needs provider validation. This preserves the
approved ingress requirements without claiming direct SRT-to-Pod support.
See [provider evidence](../evidence/provider-inventory.md).

No mandatory MediaMTX transport failure was observed in the qualified local paths,
so the conditional SRS contingency has not been triggered. Neither MediaMTX nor
SRS can be declared Twitch-dual-format compatible without the missing external
negotiation/delivery evidence. Keep dependent platform integration gated.
