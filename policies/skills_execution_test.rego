package agia.skills.execution

import rego.v1

valid_input := {
  "operation": "EXECUTE",
  "stage": "PRODUCTION",
  "identity": {"name": "video", "version": "1.0.0", "digest": "abc"},
  "control": {"enabled": true, "revoked": false},
  "bundle": {"digest": "def", "signature_verified": true},
}

test_allow_valid_production_execution if {
  allow with input as valid_input
}

test_deny_disabled_skill if {
  not allow with input as object.union(valid_input, {"control": {"enabled": false, "revoked": false}})
}

test_deny_revoked_skill if {
  not allow with input as object.union(valid_input, {"control": {"enabled": true, "revoked": true}})
}

test_deny_unverified_bundle if {
  not allow with input as object.union(valid_input, {"bundle": {"digest": "def", "signature_verified": false}})
}

test_deny_non_production if {
  not allow with input as object.union(valid_input, {"stage": "VALIDATED"})
}
