# Provider feasibility inventory

Reviewed 2026-09-30 against official documentation. AWS EC2 and RunPod **Pods**
remain the selected v1 providers. Subsequent [account preflight](m0-account-eligibility.md)
verified AWS STS/Free Tier/EC2 read APIs and RunPod console access. Regional
quotas are recorded below; GPU execution, lifecycle, media throughput and cost
attribution remain unverified. The owner authorizes eligibility checks only; lifecycle tests and
spending have no approval. No provider resources were created. Adapter version
tested: none. These records are not provider certification or an approved budget.

A later [read-only quota preflight](m0-account-eligibility.md#regional-quota-follow-up)
established `us-east-2` Standard On-Demand quota of 32 vCPUs and zero G/VT and P
GPU vCPU quotas for the signed-in project. GPU instance types are offered in the
regional catalog, but those offers do not establish launch eligibility. Region
and account-specific GPU capacity remains unavailable to qualification under the
current zero quotas; no quota change was requested.

## AWS EC2

EC2's [RunInstances API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_RunInstances.html)
supports client-token idempotency, tags, explicit subnets/security groups and a
permission-checking DryRun. The implementation must persist operation/resource
IDs and reconcile inventory; a successful launch response does not prove worker
readiness. DryRun was not invoked, and does not itself prove regional capacity.

An EC2 ingress edge can be configured with TCP and UDP security-group rules;
[AWS's rule guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules-reference.html)
describes protocol/port-specific ingress. Design requirements: public TLS control
and RTMPS endpoints, explicit UDP SRT/ICE ports where needed, no public plain RTMP,
source restrictions, and a stable address/DNS independent of temporary workers.
Actual IPv4/IPv6 bindings, firewall reachability, reconnect and throughput remain
tests to run on an authorized deployment.

GPU instances require the [appropriate NVIDIA driver](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html).
Select an instance by exact GPU encode/decode capabilities, not CUDA availability
alone. Pin the AMI, driver, container and FFmpeg build; prove device access and a
real encode before capacity admission. CPU relay operation does not need a GPU.
No instance family is certified by this record.

[Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-api.html)
is a separate API capability from EC2 provisioning. Account enablement, payer/member
permissions, cost-allocation tags, data freshness, resource attribution and query
charges require separate evidence. Estimates must retain price source/time and
currency; usage-derived estimates must never be labeled as reported actual costs.
Include compute, storage, public address and network charges when applicable.

## RunPod Pods

The [Pod creation API](https://docs.runpod.io/api-reference/pods/POST/pods) exposes
GPU count/type selection, image, storage, port and minimum bandwidth settings.
Returned port mappings must be discovered after readiness. A requested bandwidth
minimum is not measured media throughput or an SLA. Persist Pod IDs; names are not
unique and are insufficient ownership identifiers.

The [port-exposure documentation](https://docs.runpod.io/pods/configuration/expose-ports)
explicitly says Pods do not support UDP connections and describes HTTP or direct
TCP exposure. External port mappings can change after reset. Consequently, direct
SRT ingest and direct UDP WebRTC on a Pod cannot be assumed. The agreed stable
ingress edge must terminate SRT and forward over an authenticated encrypted TCP
path; workers publish directly outward. Preview can use an edge relay or a proven
TCP/TURN route. These are implementation requirements/inferences, not tested
provider paths. Preserve SRT support at the edge rather than dropping the feature.
The HTTP proxy is not a generic RTMP or SRT tunnel.

The [Pod billing history API](https://docs.runpod.io/api-reference/billing/GET/billing/pods)
returns amounts and billed time, supports Pod-ID filtering/grouping and time
periods. This is a documented reported-cost capability, not merely an hourly-price
estimate. Actual account access, units/currency, latency, pagination/time coverage,
credits, storage attribution and reconciliation with invoices remain unverified.
Keep each cost source's provenance and do not claim full attribution from a rate
field on a Pod object.

## Shared GPU/container admission requirements

Use the exact GPU entry in NVIDIA's [video support matrix](https://developer.nvidia.com/video-encode-decode-support-matrix)
to check codec, pixel format and session limitations. NVIDIA's
[container runtime documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html)
distinguishes visible devices from driver capabilities; video encode/decode needs
the `video` capability. A CUDA-only container or `nvidia-smi` result is not a video
encode test. Admission must run the actual required encode/filter/decode path,
record driver/device IDs and measure capacity. No cloud GPU test was performed.

The NVIDIA live skill catalog was checked; no strong NVENC/provider-feasibility
skill match was found, so this review uses the primary documentation above.
No skill, driver or GPU runtime was installed or changed.

## Remaining external gates

AWS: IAM/region/quota and launch/restart/terminate reconciliation, owned-resource
cleanup, network/device execution, Cost Explorer authorization and actual cost
attribution. RunPod: Pod lifecycle and port discovery, TCP media/preview topology,
GPU execution, interruption recovery, storage cleanup and billing reconciliation.
AWS project identity is verified privately; RunPod API authorization and spending
authorization remain absent. The AWS Free Plan has credits, but they are not an
approved test budget. These remain acceptance gates, not reasons to remove either
provider from v1.
