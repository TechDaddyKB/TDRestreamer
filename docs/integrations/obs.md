# OBS integration

Target v1 uses OBS's Custom streaming service with authenticated RTMP/RTMPS/SRT
inputs. Standard, independent horizontal/vertical, and combined-canvas modes are
required. No custom OBS plugin is planned.

**Current build:** input identities/tokens can be created, but there is no running
application ingress listener. Do not enter a development input token into an
external service or expect OBS to connect to port 1935.

The local feasibility spike uses synthetic H.264 and separately identifiable AAC
tracks. It does not prove real OBS packaging, platform track meaning, dual-output
setup or live/VOD behavior. Those remain explicit M0 gates. Multi-track and multi-
channel audio are different; the chosen track must never silently fall back.
