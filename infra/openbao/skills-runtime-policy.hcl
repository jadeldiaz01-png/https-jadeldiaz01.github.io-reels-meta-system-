path "transit/verify/skills-runtime/*" {
  capabilities = ["update"]
}

path "transit/keys/skills-runtime" {
  capabilities = ["read"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
