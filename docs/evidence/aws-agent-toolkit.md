# AWS Agent Toolkit setup

Date: 2026-09-30. This is developer-tool installation evidence, not cloud worker
qualification or authorization to deploy or broadcast.

## Configuration

- AWS experience: new; project: Index Zero; selected Region: `us-east-2`.
- Named CLI profile selected by the owner: `index-zero`.
- AWS CLI `2.37.6`, installed using AWS's official user-local Linux installer.
- Browser login completed by the owner; `sts get-caller-identity` succeeded.
- Toolkit setup used `us-east-1`, its required service Region. Project resource
  operations remain restricted to `us-east-2`.
- The installer added 24 default skills to Claude Code, Codex/OpenCode's shared
  skills directory, and Pi. It configured AWS MCP for Claude Code, Codex, and
  OpenCode; Pi has no automated MCP setup in this installer.
- Each generated MCP entry now selects `index-zero` via
  `AWS_MCP_PROXY_PROFILES` (`environment` in OpenCode, `env` elsewhere).
  Generated commands and arguments were preserved.
- The remote toolkit catalog returned 114 available skills.
- An independent MCP client completed initialization and `tools/list`, receiving
  eight tools. No resource-operation tool was called.

The CLI and MCP configuration are user-local and are not committed. No credentials,
login caches, project identifiers, or private configuration files are included.
Project guidance is in [AGENTS.md](../../AGENTS.md) and
[CLAUDE.md](../../CLAUDE.md), with local authorization taking precedence over the
delimited upstream AWS rules. Both files were absent before setup.

## Renewal and activation

Restart the AI coding tool/session to load its new MCP configuration and skills.
AWS's setup guide states that login credentials last 12 hours and can be renewed
for 90 days without another browser sign-in. To sign in again:

```sh
aws login --region us-east-2 --profile index-zero
aws sts get-caller-identity --profile index-zero
```

For another project, use `aws login --profile <name>`, add its profile name to the
space-separated `AWS_MCP_PROXY_PROFILES` list in each MCP configuration, and restart
the AI tool. Do not commit credentials or expose them in diagnostic output.

## Boundaries

Only account eligibility checks are currently authorized. No resource provisioning,
paid-plan upgrades, funding, or broadcasts were performed by this setup. M0's real
platform-delivery gates and cloud lifecycle/device/billing qualification remain
unverified. Toolkit connectivity is not evidence of those capabilities.

Sources: [AWS setup instructions](https://raw.githubusercontent.com/aws/agent-toolkit-for-aws/refs/heads/main/setup-instructions/setup.md),
[new-experience rules](https://raw.githubusercontent.com/aws/agent-toolkit-for-aws/refs/heads/main/rules/aws-starter-rules.md),
[OpenCode MCP schema](https://opencode.ai/docs/mcp-servers/).
