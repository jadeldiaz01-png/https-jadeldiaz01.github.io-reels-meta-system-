package revenue_engine.authz

import rego.v1

default allow := false

default approval_required := false

external_writes := {"publish_reel", "create_offer", "fulfill_order", "customer_message", "change_price"}
human_actions := {"create_offer", "change_price"}

forbidden(req) if req.payload.requires_captcha_bypass == true
forbidden(req) if req.payload.anti_bot_bypass == true
forbidden(req) if req.payload.impersonation == true
forbidden(req) if req.payload.fake_engagement == true
forbidden(req) if req.payload.copyright_status == "unverified"
forbidden(req) if req.kill_switch == true

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

external_disabled(req) if {
  req.action_class in external_writes
  req.external_execution_enabled != true
}

decision := {
  "allowed": allow,
  "approval_required": approval_required,
  "policy": "revenue_engine.authz.v1"
}
