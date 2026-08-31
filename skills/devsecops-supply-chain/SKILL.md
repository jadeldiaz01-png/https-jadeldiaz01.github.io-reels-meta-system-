---
name: devsecops-supply-chain
version: 1.0.0
domain: devsecops
---
# DevSecOps Supply Chain Skill

Assess a build/release evidence bundle for security and supply-chain readiness.

Required evidence includes tests, dependency scanning, secret scanning, SBOM, provenance and artifact signature verification. Missing mandatory evidence fails closed.

This skill evaluates evidence only; it does not deploy, sign with production credentials, rotate secrets or modify protected branches.
