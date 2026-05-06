"""Environment variable configuration for the Reducto MCP server."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

REDUCTO_DIR = Path.home() / ".reducto"
CONFIG_PATH = REDUCTO_DIR / "config.yaml"

CLIENT_ID = "mcp-server-reducto"

TRANSPORT_STDIO = "stdio"
TRANSPORT_HOSTED = "hosted"

STUDIO_API_URL_DEFAULT = "https://mild-moose-423.convex.site"


def _parse_config(content: str) -> dict:
    """Minimal YAML parser for ~/.reducto/config.yaml.

    Handles two formats:
      Legacy flat:    api_key: xxx
      Per-client:     credentials:
                        mcp-server-reducto:
                          api_key: xxx
    """
    result: dict = {}
    current_section: str | None = None
    current_client: str | None = None

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0 and ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key == "credentials" and not value:
                current_section = "credentials"
                result.setdefault("credentials", {})
            else:
                current_section = None
                current_client = None
                if value:
                    result[key] = value
        elif current_section == "credentials" and indent >= 2:
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                if not value and indent < 4:
                    current_client = key
                    result["credentials"].setdefault(current_client, {})
                elif current_client and indent >= 4:
                    result["credentials"][current_client][key] = value

    return result


def read_saved_api_key(client_id: str = CLIENT_ID) -> str | None:
    """Read API key from ~/.reducto/config.yaml.

    Resolution: client-specific key first, then any other client's key,
    then legacy flat api_key for backward compatibility.
    """
    try:
        content = CONFIG_PATH.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None

    config = _parse_config(content)
    credentials = config.get("credentials", {})

    # 1. This client's key
    own = credentials.get(client_id, {}).get("api_key")
    if own:
        return own

    # 2. Any other client's key (fallback so `reducto login` works for MCP too)
    for cid, cred in credentials.items():
        if cid != client_id:
            key = cred.get("api_key")
            if key:
                return key

    # 3. Legacy flat format
    legacy = config.get("api_key")
    if legacy:
        return legacy

    return None


def write_api_key(value: str, client_id: str = CLIENT_ID) -> None:
    """Write API key to ~/.reducto/config.yaml under the client's credential section.

    Preserves other clients' credentials. Migrates legacy flat format.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Read existing config
    try:
        content = CONFIG_PATH.read_text(encoding="utf-8")
        config = _parse_config(content)
    except (FileNotFoundError, OSError):
        config = {}

    credentials = config.get("credentials", {})
    credentials[client_id] = {"api_key": value.strip()}

    # Write back in per-client format
    lines = []
    # Preserve non-credential top-level keys (but drop legacy api_key)
    for key, val in config.items():
        if key not in ("credentials", "api_key"):
            lines.append(f"{key}: {val}")

    lines.append("credentials:")
    for cid, cred in credentials.items():
        lines.append(f"  {cid}:")
        for k, v in cred.items():
            lines.append(f"    {k}: {v}")

    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with contextlib.suppress(OSError):
        os.chmod(CONFIG_PATH, 0o600)


def get_api_key() -> str:
    """Get the Reducto API key.

    Resolution order:
    1. REDUCTO_API_KEY environment variable
    2. ~/.reducto/config.yaml (this client first, then fallback to other clients)

    Raises RuntimeError with actionable guidance if no key is found.
    """
    # 1. Environment variable (highest priority)
    env_value = os.environ.get("REDUCTO_API_KEY")
    if env_value and env_value.strip():
        return env_value.strip()

    # 2. Config file
    saved_value = read_saved_api_key()
    if saved_value:
        return saved_value

    raise RuntimeError(
        "No Reducto API key found. To authenticate, either:\n"
        "  1. Run: mcp-server-reducto --login  (opens browser, saves key automatically)\n"
        "  2. Run: reducto login  (if you have the Reducto CLI installed)\n"
        "  3. Set REDUCTO_API_KEY environment variable\n"
        "  4. Get a key at https://studio.reducto.ai/api-keys and add it to your MCP client config"
    )


def get_studio_api_url() -> str:
    """Get the Studio API URL for device auth flow."""
    return os.environ.get("REDUCTO_STUDIO_API_URL", STUDIO_API_URL_DEFAULT)


def get_base_url() -> str | None:
    """Get optional base URL override (for EU/on-prem deployments)."""
    return os.environ.get("REDUCTO_BASE_URL")


def get_timeout() -> float:
    """Get sync request timeout in seconds."""
    return float(os.environ.get("REDUCTO_MCP_TIMEOUT", "300"))


def get_max_response_size() -> int:
    """Get max response size in characters before truncation."""
    return int(os.environ.get("REDUCTO_MCP_MAX_RESPONSE_SIZE", "50000"))


def get_transport() -> str:
    """Get MCP transport mode: 'stdio' or 'http'."""
    return os.environ.get("REDUCTO_MCP_TRANSPORT", "stdio")


def get_port() -> int:
    """Get port for HTTP transport."""
    return int(os.environ.get("REDUCTO_MCP_PORT", "8000"))
