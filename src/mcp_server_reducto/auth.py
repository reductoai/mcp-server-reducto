"""Device code authentication flow for the Reducto MCP server.

Implements OAuth 2.0 Device Authorization Grant against the same
Convex backend used by the Reducto CLI. This allows users to
authenticate via browser without manually copying API keys.

The flow:
1. Request device code from studio API
2. Open browser to verification URL
3. Poll until user approves (or timeout)
4. Save API key to ~/.reducto/config.yaml (shared with CLI)
"""

from __future__ import annotations

import asyncio
import platform
import sys
import time
import webbrowser

import httpx

from mcp_server_reducto import __version__
from mcp_server_reducto.config import CLIENT_ID, get_studio_api_url, read_saved_api_key, write_api_key


class AuthError(Exception):
    """Raised when device auth flow fails."""


def _print(msg: str) -> None:
    """Print to stderr (stdout may be the MCP transport)."""
    print(msg, file=sys.stderr, flush=True)


async def device_auth_login(*, force: bool = False) -> str:
    """Run the device code authentication flow.

    Opens the user's browser to approve the request, polls for approval,
    and saves the API key to ~/.reducto/config.yaml.

    Args:
        force: If True, skip the existing-key confirmation prompt.

    Returns:
        The API key string.

    Raises:
        AuthError: If authentication fails, is denied, or times out.
    """
    # Check for existing key
    existing_key = read_saved_api_key()
    if existing_key and not force:
        _print("An API key is already saved at ~/.reducto/config.yaml")
        _print("Use --login --force to replace it, or just start the server.")
        return existing_key

    client_info = {
        "client_id": CLIENT_ID,
        "client_display_name": "Reducto MCP Server",
        "client_version": __version__,
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
    }

    studio_url = get_studio_api_url()

    async with httpx.AsyncClient() as client:
        # Step 1: Request device code
        try:
            response = await client.post(
                f"{studio_url}/deviceAuth/deviceCode",
                json={"clientInfo": client_info},
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise AuthError(f"Failed to request device code: {e}") from e

        auth_data = response.json()
        device_code: str = auth_data["device_code"]
        user_code: str = auth_data["user_code"]
        verification_uri: str = auth_data["verification_uri_complete"]
        interval: int = auth_data["interval"]
        expires_in: int = auth_data["expires_in"]

        # Step 2: Show instructions
        _print("")
        _print("Reducto MCP Server — Authentication")
        _print(f"  Your code:  {user_code}")
        _print(f"  Visit:      {verification_uri}")
        _print(f"  Expires in: {expires_in}s")
        _print("")

        # Step 3: Open browser
        try:
            webbrowser.open(verification_uri)
            _print("Browser opened automatically.")
        except Exception:
            _print("Could not open browser — please visit the URL above manually.")

        # Step 4: Poll for approval
        _print("Waiting for approval...")
        start_time = time.monotonic()

        while time.monotonic() - start_time < expires_in:
            await asyncio.sleep(interval)

            try:
                poll_response = await client.post(
                    f"{studio_url}/deviceAuth/poll",
                    json={"device_code": device_code},
                    timeout=10.0,
                )
                poll_response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    error_data = e.response.json()
                    if error_data.get("error") == "slow_down":
                        await asyncio.sleep(interval)
                        continue
                raise AuthError(f"Polling failed: {e}") from e
            except httpx.HTTPError as e:
                raise AuthError(f"Polling failed: {e}") from e

            poll_data = poll_response.json()
            status = poll_data["status"]

            if status == "approved":
                api_key: str = poll_data["api_key"]
                write_api_key(api_key)
                _print("Authentication successful! API key saved to ~/.reducto/config.yaml")
                return api_key

            if status == "denied":
                raise AuthError("Authentication denied by user.")

            if status == "expired":
                raise AuthError("Authentication session expired. Please try again.")

            # status == "pending" — continue polling

        raise AuthError(f"Authentication timed out after {expires_in}s. Please try again.")
