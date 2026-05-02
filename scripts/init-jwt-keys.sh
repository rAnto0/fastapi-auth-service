#!/usr/bin/env bash
set -euo pipefail

bits=2048
force=0

usage() {
  cat <<'USAGE'
Usage: scripts/init-jwt-keys.sh [--force] [--bits N]

Generate RSA key pair for this auth service.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      force=1
      shift
      ;;
    --bits)
      bits="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if ! command -v openssl >/dev/null 2>&1; then
  echo "OpenSSL is not installed."
  exit 1
fi

if [[ ! "$bits" =~ ^[0-9]+$ ]]; then
  echo "--bits must be a positive integer"
  exit 1
fi

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
certs_dir="$root_dir/app/core/certs"
private_key="$certs_dir/jwt-private.pem"
public_key="$certs_dir/jwt-public.pem"

mkdir -p "$certs_dir"

if [[ "$force" -eq 0 && ( -f "$private_key" || -f "$public_key" ) ]]; then
  echo "Keys already exist. Use --force to regenerate."
  exit 0
fi

rm -f "$private_key" "$public_key"

echo "Generating RSA keys ($bits bits) in $certs_dir"
openssl genpkey -algorithm RSA -pkeyopt "rsa_keygen_bits:$bits" -out "$private_key"
openssl rsa -in "$private_key" -pubout -out "$public_key"

chmod 600 "$private_key"
chmod 644 "$public_key"

echo "Done:"
echo "  private: $private_key"
echo "  public : $public_key"
