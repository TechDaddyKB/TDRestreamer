# Capability and feasibility record

Reviewed 2026-09-30. These records distinguish documentation, code and tested behavior.

| Component | Evidence / source | Remaining gate |
|---|---|---|
| MediaMTX 1.21.1 / FFmpeg 9.0.1 | Synthetic transport spike plus real OBS dual-audio and Chromium WebRTC/HLS fallback; RTMPS/encrypted-SRT preservation and denials; see [local qualification](m0-local.md) | Twitch semantics, additional OBS modes, production supervision |
| YouTube H/V | https://developers.google.com/youtube/v3/live/docs | OAuth scopes/approval, broadcast association and real-account delivery |
| Twitch H/V | https://dev.twitch.tv/docs/video-broadcast/ and https://help.twitch.tv/s/article/multiple-encodes | Dashboard reports Dual Format eligibility; Enhanced Broadcasting negotiation and delivery remain unverified; ordinary two-key fanout is not proof |
| Kick | https://docs.kick.com/ | Authenticated setup access observed; application API permissions and delivery not verified |
| X | https://docs.x.com/ | Live Studio access observed; developer enrollment and supported broadcast API operations not verified |
| Rumble | Platform/account-specific workflow required | Authenticated setup access observed; application API permissions and delivery not verified |
| AWS | https://docs.aws.amazon.com/AWSEC2/latest/APIReference/Welcome.html and https://docs.aws.amazon.com/cost-management/latest/userguide/ce-api.html | Free Plan and EC2 read access verified; no implemented adapter or billable lifecycle test |
| RunPod | https://docs.runpod.io/api-reference/overview | No implemented adapter; network/GPU requirements and reported billing API documented; console access observed; API and lifecycle behavior unverified |

MediaMTX multiple-track FFmpeg requirements:
https://mediamtx.org/docs/read/ffmpeg . The local spike is not complete platform
acceptance. The owner now authorizes account eligibility checks; external broadcasts,
cloud provisioning and spending require separate approval.

Detailed, dated records: [platform inventory](platform-inventory.md) and
[provider inventory](provider-inventory.md). The [authenticated eligibility record](m0-account-eligibility.md)
separates verified dashboard/AWS read access from remaining OAuth, API and delivery gates.
