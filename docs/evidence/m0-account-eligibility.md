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

## Developer-console observations

These follow-up checks also stopped before any registration, consent, credential
creation, or billable API request:

- Twitch's authenticated developer console lists an existing unrelated app. The
  new-application form is accessible and offers public/confidential client types
  and redirect URI configuration. No Restreamer app or consent grant was created.
- Kick's authenticated developer page explicitly reports **No KICK App**. Its
  creation form is accessible with scope choices for user information, stream-key
  read, channel read/update and other features. The form states creation accepts
  terms; it was left unsubmitted. Scope choices are not granted permissions.
- Google Cloud APIs & Services is accessible. The project picker search for
  `restream` returned **No resources to display**. This is only a name search,
  not proof that no usable OAuth client exists under another project. No existing
  project, enabled service or OAuth consent configuration was changed.
- X's legacy developer portal links to the current `console.x.com`. For the
  signed-in profile, that console presents **Create a developer account** and
  **Start Building**, with pay-per-use API access described. Enrollment was not
  submitted. Existing Live Studio access does not establish enrollment or a
  supported public broadcast-lifecycle API.

### Signed-in Chrome recheck

On 2026-09-30, the owner approved a local read-only connection to their running
Google Chrome 154 session. The Chrome DevTools MCP client was pinned to 1.10.1
for this check with input actions and JavaScript evaluation disabled. No browser
profile or cookie files were read. The observed account state was:

| Platform | Current developer/API access observation | Limit |
|---|---|---|
| Twitch | The registered-app list contains one unrelated app and no Restreamer app. The prepared Restreamer form remains unsubmitted. | No Restreamer client, grant, or Enhanced Broadcasting negotiation was established. |
| Kick | The signed-in Developer settings page says **No KICK App**. | No app registration, scopes, or token flow was tested. |
| X | The developer console still presents **Create a developer account**. | Producer/Live Studio UI access does not establish X API enrollment or public lifecycle controls. |
| Google Cloud / YouTube | The selected existing project is unrelated to Restreamer and shows no OAuth clients. | Other projects and YouTube publishing grants were not qualified; the selected project was not changed. |
| Rumble | The Livestream API settings page loads and offers user/channel sections. | No credential-bearing API URL was opened or copied, and no API request or control operation was tested. |

These were UI observations at the time of the read-only recheck. A later,
separately approved Twitch app registration and app-token test are recorded below.
The browser connection did not expose stream keys or API URLs in the retained record.

For platforms other than Twitch, next prerequisites remain a dedicated
app/callback configuration and consent plan, plus explicit approval wherever
registration creates credentials or accepts terms. No existing unrelated app
will be reused or modified implicitly. X developer enrollment, API product
suitability and any associated charges need separate resolution; a normal X
account is insufficient evidence. Rumble Live Stream API invocation remains untested.

### Approved Twitch app registration and API read

On 2026-09-30, the owner approved the exact dedicated Twitch registration and
signed in to a separate Chrome profile. The app `Tech Daddy's Restreamer M0`
was registered under TechDaddy with Broadcaster Suite category, confidential
client type and `http://localhost:18971/oauth/twitch/callback` redirect. Its
client ID and newly generated secret were stored in the local Secret Service
keyring; the secret-bearing tab was closed. The
[reproducible read-only preflight](../../tests/m0/twitch-app-token.mjs) obtained
an app token and read the public TechDaddy Helix user record. The
[sanitized report](m0-twitch-app-token.json) records HTTP 200 for both calls
and one matching user. No token or credential was retained in the report.

This proves only client-credentials authentication and a public API read.
No broadcaster OAuth consent, scope grant, refresh/revocation, stream-key access,
Twitch H/V negotiation, or broadcast was performed. Other platform API gates
remain open. See the [Twitch procedure](m0-twitch-qualification.md).

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
or availability of every operation under the new AWS experience. A later
permission-only DryRun is recorded below; Cost Explorer queries were not made.
Free Plan expiry is distinct from the credit instrument's expiry shown in AWS
Settings.

### Regional quota follow-up

On 2026-09-30, the authenticated `index-zero` profile again passed STS identity
verification. Reproduce the read-only quota and regional-offering queries with
the explicit project profile and selected Region (do not publish account IDs or
other raw identity output):

```sh
aws service-quotas list-service-quotas --service-code ec2 \
  --region us-east-2 --profile index-zero \
  --query 'Quotas[?contains(QuotaName, `Running On-Demand`)].{Name:QuotaName,Code:QuotaCode,Value:Value}' \
  --output json
aws ec2 describe-instance-type-offerings --location-type region \
  --filters Name=instance-type,Values=g4dn.xlarge,g5.xlarge,g6.xlarge \
  --region us-east-2 --profile index-zero \
  --query 'InstanceTypeOfferings[].InstanceType' --output json
```

The quota response returned these account-specific On-Demand vCPU limits:

| Quota | Code | Limit (vCPUs) |
|---|---|---:|
| Standard (A, C, D, H, I, M, R, T, Z) | `L-1216C47A` | 32 |
| G and VT | `L-DB2E81BA` | 0 |
| P | `L-417A185B` | 0 |

`describe-instance-type-offerings` listed `g4dn.xlarge`, `g5.xlarge`, and
`g6.xlarge` for the Region. An offering means the type appears in the regional
catalog; it does not override the zero GPU vCPU quota or prove available capacity,
Free Plan eligibility, launch authorization, driver access, or codec performance.
AWS [defines these On-Demand limits as vCPU quotas](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html)
and [describes the offerings API as a location catalog](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeInstanceTypeOfferings.html).
No quota increase was requested. GPU qualification on this AWS project requires
a separate eligibility and spending decision before any launch attempt.

### Non-launching EC2 permission check

On 2026-09-30 the official AWS MCP connection returned the same Free Plan expiry
as the `index-zero` CLI preflight above, consistent with the same project. It
found an available default VPC in `us-east-2` and resolved AWS's
public Amazon Linux 2023 x86-64 AMI parameter. A single `RunInstances` call for
one `t3.micro`, with `DryRun=True`, returned `DryRunOperation`. Per the
[EC2 API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_RunInstances.html),
this response means the principal has the permissions for that specific
operation without launching an instance. No instance or other resource was
created. The result does **not** establish successful launch, available capacity,
network reachability, media performance, GPU launch eligibility, cleanup rights,
or billed cost attribution. No GPU DryRun was attempted; the account's G/VT and
P GPU vCPU quotas remain zero. The AMI ID, VPC ID, principal and account ID are
omitted from this public record.

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
still pending. Twitch H/V delivery and live/VOD semantics require a successful
separately approved broadcast test. Neither this record nor successful AWS
authentication closes that gate. See the [gate audit](m0-gates.md).

A later separately approved [Twitch diagnostic attempt](m0-twitch-live-attempts.md)
established an account-specific negotiated ladder, but both bounded publisher
attempts failed before viewer/VOD verification. Its approval is exhausted. The
observations above remain the eligibility preflight at their recorded time.
