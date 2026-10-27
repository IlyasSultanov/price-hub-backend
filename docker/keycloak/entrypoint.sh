#!/bin/bash
set -euo pipefail

realm_export_file_path="/opt/keycloak/data/import-template/realm-export-price-hub.json"

if [ -f "$realm_export_file_path" ]; then
    rendered_realm="$(<"$realm_export_file_path")"
    while [[ "$rendered_realm" =~ __ENV_([A-Z][A-Z0-9_]*)__ ]]; do
        variable_name="${BASH_REMATCH[1]}"
        if [[ ! -v "$variable_name" ]]; then
            echo "Missing environment variable $variable_name for local realm import" >&2
            exit 1
        fi

        variable_value="${!variable_name}"
        if [[ ! "$variable_value" =~ ^[A-Za-z0-9._~+:/=-]+$ ]] ||
           [[ "$variable_value" == *__ENV_* ]]; then
            echo "Invalid value of $variable_name for local realm import" >&2
            exit 1
        fi

        marker="__ENV_${variable_name}__"
        rendered_realm="${rendered_realm//"$marker"/"$variable_value"}"
    done

    umask 077
    mkdir -p /opt/keycloak/data/import
    rendered_realm_file="/opt/keycloak/data/import/price-hub-realm.json"
    printf '%s\n' "$rendered_realm" > "$rendered_realm_file"
    if [[ "${1:-}" == "start" || "${1:-}" == "start-dev" ]]; then
        set -- "$@" --import-realm
    fi
fi

exec /opt/keycloak/bin/kc.sh "$@"
