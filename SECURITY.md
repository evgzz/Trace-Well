# Security Policy

TRACE-Well V1.5 is a deterministic engineering evaluation prototype, not a production security control or clinical safety system.

## Supported scope

Security reports should concern the public repository implementation, including:

- unsafe handling of local files or paths;
- dependency or packaging vulnerabilities;
- evidence-file integrity defects;
- publication-scan bypasses that expose tracked private context;
- external-trace parsing defects that can corrupt or misclassify evidence;
- credential or secret exposure introduced by repository code.

## Out of scope

V1.5 does not provide production IAM, network security controls, multi-tenant isolation, secret management, or live clinical connectivity.

## Reporting

Use the repository's private security-reporting mechanism when available. Do not publish exploit details or private information in a public issue.

## Sensitive data

Do not submit PHI, live patient records, production credentials, private customer data, or other secrets as test fixtures or issue attachments.

## Claims boundary

A passing TRACE-Well evaluation does not establish that an evaluated system is secure, clinically safe, or production ready. See `docs/LIMITATIONS.md`.
