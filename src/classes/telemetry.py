"""
Telemetry client for sharing anonymous usage data with the Riverscapes team.
This helps us understand how our tools are used and prioritize improvements.
"""

from __future__ import annotations

import json
import os
import platform
from threading import Thread
from urllib.parse import urlparse
import urllib.request
from urllib.request import Request
import uuid

from qgis.core import Qgis

from ...__version__ import __version__
from .settings import Settings


class Telemetry:
    def __init__(self, app_name: str, version: str | None = None):
        """Initialize the Telemetry client.

        Args:
            app_name (str): The name of the application.
            version (str | None, optional): The version of the application. Defaults to the Riverscapes Viewer plugin version.
        """
        self.app_name = app_name.replace(" ", "_")
        self.version = version if version is not None else __version__
        self.settings = Settings()

    def _load_secrets(self) -> tuple[str | None, str | None]:
        # secrets.json lives two directories above this file (at the plugin root)
        secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "secrets.json"))
        try:
            with open(secrets_path, encoding="utf-8") as f:
                secrets = json.load(f)
            telemetry_cfg = secrets.get("telemetry", {})
            api_url = telemetry_cfg.get("api-url")
            api_token = telemetry_cfg.get("api-token")
            if api_url and api_token:
                endpoint = f"{api_url}/ingest/ping"
                token = api_token
                return endpoint, token
        except FileNotFoundError:
            self.settings.log(f"Telemetry: secrets.json not found at {secrets_path}; telemetry disabled.", Qgis.Info)
        except Exception as e:
            self.settings.log(f"Telemetry: failed reading secrets ({e}).", Qgis.Warning)

        return None, None

    def get_client_id(self) -> str:
        # Check if a client ID already exists in settings, if not generate a new one and save it
        client_id = self.settings.getValue("telemetryClientId")
        if not client_id:
            client_id = str(uuid.uuid4())
            self.settings.setValue("telemetryClientId", client_id)
        return client_id

    def send(self, event: str, use_telemetry: bool | None = None) -> None:
        """Send a telemetry event in a background thread.

        Args:
            event (str): The name of the event to send.
            use_telemetry (bool | None, optional): Whether to use telemetry. This should come from the settings of the app making the call. Defaults to None.
        """

        app_name = self.app_name
        client_id = self.get_client_id()

        use_telemetry = self.settings.getValue("telemetryEnabled") if use_telemetry is None else use_telemetry
        endpoint, token = self._load_secrets()

        if use_telemetry is not True:
            self.settings.log("Telemetry: disabled by settings (telemetryEnabled=False).", Qgis.Info)
            return

        if not client_id:
            self.settings.log("Telemetry: missing client_id; skipping send.", Qgis.Warning)
            return

        if not endpoint or not token:
            self.settings.log("Telemetry: missing endpoint/token; skipping send.", Qgis.Info)
            return

        self.settings.log(f'Telemetry: queueing event "{event}".', Qgis.Info)

        settings = self.settings

        def _send():
            try:
                payload = json.dumps(
                    {
                        "app_name": app_name,
                        "app_version": self.version,
                        "os_platform": platform.system().lower(),
                        "client_id": client_id,
                        "event": event,
                    }
                ).encode("utf-8")

                parsed = urlparse(endpoint)
                if parsed.scheme not in ("http", "https"):
                    settings.log(f'Telemetry: rejected endpoint with disallowed scheme "{parsed.scheme}".', Qgis.Warning)
                    return

                req = Request(
                    endpoint,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-telemetry-token": token,
                    },
                    method="POST",
                )
                # Build a restricted opener that only handles http/https,
                # preventing file:// or other schemes from ever being used.
                _opener = urllib.request.build_opener(
                    urllib.request.HTTPHandler,
                    urllib.request.HTTPSHandler,
                )
                with _opener.open(req, timeout=5) as response:
                    settings.log(f'Telemetry: event "{event}" sent (status={response.getcode()} url={endpoint}).', Qgis.Info)
            except Exception as e:
                settings.log(f'Telemetry: failed to send event "{event}" ({e}).', Qgis.Warning)

        Thread(target=_send, daemon=True).start()
