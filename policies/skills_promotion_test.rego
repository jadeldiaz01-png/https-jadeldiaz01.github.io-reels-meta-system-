package agia.skills.promotion_test

import data.agia.skills.promotion
import rego.v1

base := {
  "identity": {"name": "example", "version": "1.0.0", "digest": "sha256:abc"},
  "manifest": {"self_promotion": false, "external_writes": false},
  "evidence": {
    "review_passed": true,
    "tests_passed": true,
    "evals_passed": true,
    "security_passed": true,
    "policy_passed": true,
    "signature_verified": true,
    "critical_human_approval": false,
    "ci_run_id": "ci-123"
  }
}

test_validated_allowed if {
  input := object.union(base, {"from": "TESTED", "to": "VALIDATED"})
  promotion.allow with input as input
}

test_production_denied_without_human if {
  input := object.union(base, {"from": "VALIDATED", "to": "PRODUCTION"})
  not promotion.allow with input as input
  promotion.requires_human_approval with input as input
}

test_production_allowed_with_human if {
  evidence := object.union(base.evidence, {"critical_human_approval": true})
  candidate := object.union(base, {"evidence": evidence})
  input := object.union(candidate, {"from": "VALIDATED", "to": "PRODUCTION"})
  promotion.allow with input as input
}

test_non_sequential_denied if {
  input := object.union(base, {"from": "DRAFT", "to": "VALIDATED"})
  not promotion.allow with input as input
}
