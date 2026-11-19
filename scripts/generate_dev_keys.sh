#!/usr/bin/env bash
set -euo pipefail

mkdir -p secrets
if [[ ! -f secrets/jwt_private.pem ]]; then
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out secrets/jwt_private.pem
fi
if [[ ! -f secrets/jwt_public.pem ]]; then
  openssl pkey -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem
fi
chmod 600 secrets/jwt_private.pem
chmod 644 secrets/jwt_public.pem
printf 'Development keypair ready in secrets/ (never commit these files).\n'
