package revenue_engine.authz

import rego.v1

default allow := false

default approval_required := false

external_writes := {"publish_reel", "create_offer", "fulfill_order", "customer_message", "change_price"}
human_actions := {"create_offer", "change_price"}

forbidden(input) if input.payload.requires_captcha_bypass == true
forbidden(input) if input.payload.anti_bot_bypass == true
forbidden(input) if input.payload.impersonation == true
forbidden(input) if input.payload.fake_engagement == true
forbidden(input) if input.payload.copyright_status == "unverified"
forbidden(input) if input.kill_switch == true

approval_required if {
  input.action_class in human_actions
  not input.approved
}

allow if {
  input.idempotency_key != ""
  not forbidden(input)
  not approval_required
  not external_disabled(input)
}

external_disabled(input) if {
  input.action_class in external_writes
  input.external_execution_enabled != true
}

decision := {
  "allowed": allow,
  "approval_required": approval_required,
  "policy": "revenue_engine.authz.v1"
}
