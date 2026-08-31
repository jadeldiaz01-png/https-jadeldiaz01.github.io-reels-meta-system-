path "transit/sign/skills-runtime" {
  capabilities = ["update"]
}

path "transit/verify/skills-runtime" {
  capabilities = ["update"]
}

# Runtime must not manage keys, mounts, auth methods, or policies.
path "transit/keys/*" {
  capabilities = ["deny"]
}

path "sys/*" {
  capabilities = ["deny"]
}
