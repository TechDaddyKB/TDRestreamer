# Security

This development build is not approved for public production deployment.
Report vulnerabilities through the repository's private security reporting feature;
do not include credentials in public issues. If private reporting is unavailable,
contact the repository maintainer privately before sharing details.

Tenant checks, test-mode isolation and write-only secrets are security boundaries.
Keep database credentials, encryption keys, bootstrap tokens and OAuth credentials
outside Git. TLS is mandatory outside a trusted LAN. Root-level host access can
inspect worker processes; application secrecy is not protection from host root.

See docs/operations/security.md for implementation boundaries and known gaps.
