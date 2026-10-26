"""Core-only CLI: credential status/clear without the full MCP server.

Convenience surface for consumers that install only the client/auth
core (for example Catence's worker). Deliberately does not import
tp_mcp.server, tp_mcp.tools, or tp_mcp.apps, so it works in
core-only environments and stays trivially mergeable with upstream.
"""

from __future__ import annotations

import argparse
import sys

from tp_mcp.auth import get_credential, get_storage_backend, validate_auth_sync


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tp-mcp-core",
        description="TrainingPeaks core credential utilities (no MCP server).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "auth-status",
        help="Validate the TrainingPeaks credential (env first, then keyring/encrypted file).",
    )
    sub.add_parser(
        "auth-clear",
        help="Clear stored credentials (keyring and encrypted file). The TP_AUTH_COOKIE env var is never touched.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "auth-status":
        cred = get_credential()
        if not cred.success or not cred.cookie:
            print("No TrainingPeaks credential configured.")
            return 1
        print(f"Storage backend: {get_storage_backend()}")
        result = validate_auth_sync(cred.cookie)
        print(f"Status: {result.status.value}")
        if result.athlete_id:
            print(f"Athlete ID: {result.athlete_id}")
        if result.message:
            print(result.message)
        return 0 if result.is_valid else 1
    if args.command == "auth-clear":
        from tp_mcp.auth import clear_credential

        result = clear_credential()
        print(result.message)
        return 0 if result.success else 1
    print("Unknown command.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
