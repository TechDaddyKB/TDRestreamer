# M0 account eligibility preflight

Observed: 2026-09-30. This is a sanitized, manually compiled record of browser
observations and read-only CLI results. It is not a media-delivery test report.

## Authorization

The owner replaced the original local-only restriction with: **Check account
eligibility first; approve broadcasts separately.** The owner signed into the
platforms and completed AWS project creation and CLI login. No broadcast,
provisioning, paid-plan upgrade, RunPod funding, or spending limit was authorized.
AWS credits are available; their existence is not permission to consume them.

## Platform browser observations

| Platform | Observed authenticated capability | Not established |
|---|---|---|
| Twitch | Creator Dashboard for TechDaddy reports Dual Format and 2K Streaming **Eligible**, Server Side Transcode Support **Ineligible**; Store past broadcasts and Always Publish VODs are enabled | Enhanced Broadcasting negotiation, relayed H/V metadata, both viewer orientations, live/VOD audio identity, application OAuth/API scopes and refresh/revocation |
| YouTube | Live Control Room accessible; Dual stream control is present and off; the current encoder page shows no incoming data | Dual-format API association, application publishing scopes, API quota, actual ingest/viewer delivery |
| Kick | TDDigital streaming dashboard accessible and offline; Stream URL & Key navigation available | App registration/consent, API scopes, refresh/revoke, successful authenticated ingest |
| X | Media Studio and Live Studio accessible for TechDaddyKB; Manage Sources and New Livestream controls present | Public lifecycle API eligibility, app scopes, source ingest and viewer delivery |
| Rumble | Live setup form accessible with TechDaddyKB profile and TechDaddy Gaming channel; public, unlisted, and private visibility options present | Submitted event creation, ingest endpoint protocol, Live Stream API authorization and actual delivery |

No stream keys were revealed or copied during these observations. No platform
broadcast was created or started. Browser access is evidence of those particular
controls being available, not proof of application API permissions or delivery.

## AWS read-only results

Project: Index Zero. Profile: `index-zero`. Selected Region: `us-east-2`.
CLI version: `2.37.6`. The owner completed browser login; STS identity matches the
project used in the console. Private project identifiers are omitted here.

The following commands succeeded:

```sh
aws sts get-caller-identity --profile index-zero
aws freetier get-account-plan-state --region us-east-1 --profile index-zero
aws ec2 describe-instances --region us-east-2 --profile index-zero \
  --query 'length(Reservations[].Instances[])' --output json
aws ec2 describe-instance-types --region us-east-2 --profile index-zero \
  --filters Name=free-tier-eligible,Values=true \
  --query 'InstanceTypes[].{type:InstanceType,architectures:ProcessorInfo.SupportedArchitectures,vcpus:VCpuInfo.DefaultVCpus,memoryMiB:MemoryInfo.SizeInMiB}' \
  --output json
```

The Free Tier service returned `accountPlanType=FREE`, `accountPlanStatus=ACTIVE`,
remaining credits `100.0 USD`, and plan expiry `2027-03-30T15:01:34.105000+00:00`.
The Free Tier call uses its service endpoint in `us-east-1`; no regional resources
were created there. The EC2 instance count in `us-east-2` was **0**; this is not a
global inventory of all AWS services.

The instance-type catalog returned:

| Type | Architecture | vCPUs | Memory MiB |
|---|---|---:|---:|
| t8i.micro | x86_64 | 2 | 1024 |
| t4g.small | arm64 | 2 | 2048 |
| c7i-flex.large | x86_64 | 2 | 4096 |
| t4g.micro | arm64 | 2 | 1024 |
| t3.micro | x86_64 | 2 | 1024 |
| t3.small | x86_64 | 2 | 2048 |
| m7i-flex.large | x86_64 | 2 | 8192 |
| t8i.small | x86_64 | 2 | 2048 |

This proves catalog and inventory read access. It does **not** prove launch
permission, quota, capacity, media performance, GPU support, billing attribution,
or availability of every operation under the new AWS experience. No RunInstances
or DryRun was issued; Cost Explorer queries were not made. Free Plan expiry is
distinct from the credit instrument's expiry shown in AWS Settings.

The [toolkit setup](aws-agent-toolkit.md) separately passed MCP initialization and
catalog discovery. Those tools were not used to provision anything.

## RunPod browser observation

The authenticated console is accessible and shows a **$0.00** balance. No Pod,
volume, API credential, or top-up was created. API permission, lifecycle, GPU,
media-network and billing-history behavior remain unverified. The documented
[UDP limitation](provider-inventory.md) remains relevant to the stable ingress
edge design.

## Remaining M0 decision

Account UI eligibility is partially established; application API eligibility is
still pending. Twitch's actual H/V negotiation/delivery and live/VOD semantics
require a separately approved broadcast test. Neither this record nor successful
AWS authentication closes that gate. See the [gate audit](m0-gates.md).
