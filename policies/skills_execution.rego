package agia.skills.execution

import rego.v1

default allow := false

allow if {
  input.operation == "EXECUTE"
  input.stage == "PRODUCTION"
  input.identity.name != ""
  input.identity.version != ""
  input.identity.digest != ""
  input.control.enabled == true
  input.control.revoked == false
  input.bundle.digest != ""
  input.bundle.signature_verified == true
}

execution := {
  "allow": allow,
  "operation": input.operation,
}
