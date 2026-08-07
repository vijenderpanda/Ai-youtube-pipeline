#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Provision the factory schema on a Supabase project.
#
# Use this ONLY when standing up a FRESH project. If you're pointing the worker
# at the existing project, skip this entirely — just set SUPABASE_URL /
# SUPABASE_SERVICE_KEY in secrets/factory.env.
#
#   deploy/setup-supabase.sh <project-ref>
#
# <project-ref> is the ref in your project URL: https://<ref>.supabase.co
# Requires the Supabase CLI (https://supabase.com/docs/guides/local-development)
# and an interactive `supabase login` beforehand.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

REF="${1:-}"
[[ -n "$REF" ]] || { echo "usage: deploy/setup-supabase.sh <project-ref>" >&2; exit 1; }

command -v supabase >/dev/null 2>&1 || {
  echo "✗ Supabase CLI not found. Install: https://supabase.com/docs/guides/local-development" >&2
  exit 1
}

echo "▸ Linking project $REF …"
supabase link --project-ref "$REF"

echo "▸ Applying migrations from supabase/migrations/ …"
supabase db push

echo "✓ Schema applied. Now put the project URL + service_role key in"
echo "  secrets/factory.env, then start the worker. It seeds channels/"
echo "  generators/settings rows itself on first run."
