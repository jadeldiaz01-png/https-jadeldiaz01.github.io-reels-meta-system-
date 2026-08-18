package agia.skills.promotion

import rego.v1

default allow := false

default requires_human_approval := false

valid_stage[s] if s in {"DRAFT", "REVIEWED", "TESTED", "VALIDATED", "PRODUCTION"}

sequential if {
  input.from == "DRAFT"
  input.to == "REVIEWED"
}
sequential if {
  input.from == "REVIEWED"
  input.to == "TESTED"
}
sequential if {
  input.from == "TESTED"
  input.to == "VALIDATED"
}
sequential if {
  input.from == "VALIDATED"
  input.to == "PRODUCTION"
}

base_valid if {
  valid_stage[input.from]
  valid_stage[input.to]
  sequential
  input.identity.name != ""
  input.identity.version != ""
  input.identity.digest != ""
  input.manifest.self_promotion == false
  input.manifest.external_writes == false
}

allow if {
  base_valid
  input.to == "REVIEWED"
  input.evidence.review_passed == true
}

allow if {
  base_valid
  input.to == "TESTED"
  input.evidence.tests_passed == true
  input.evidence.ci_run_id != ""
}

allow if {
  base_valid
  input.to == "VALIDATED"
  input.evidence.evals_passed == true
  input.evidence.security_passed == true
  input.evidence.policy_passed == true
  input.evidence.signature_verified == true
}

requires_human_approval if input.to == "PRODUCTION"

allow if {
  base_valid
  input.to == "PRODUCTION"
  input.evidence.signature_verified == true
  input.evidence.critical_human_approval == true
}

promotion := {
  "allow": allow,
  "requires_human_approval": requires_human_approval,
  "target": input.to,
}
