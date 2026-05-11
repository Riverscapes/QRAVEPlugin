"""
Telemetry client for sharing anonymous usage data with the Riverscapes team.
This helps us understand how our tools are used and prioritize improvements.
"""

from __future__ import annotations

import json
import os
import platform
from threading import Thread
from urllib.request import Request, urlopen
import uuid

from qgis.core import Qgis

from ...__version__ import __version__
from .settings import Settings


class Telemetry:
    def __init__(self, app_name: str):
        self.app_name = app_name.replace(" ", "_")
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

    def send(self, event: str) -> None:
        """
        Send a telemetry ping in a background thread.
        Failures are logged but never raised — telemetry must never break the app.
        """

        app_name = self.app_name
        client_id = self.get_client_id()
        use_telemetry = self.settings.getValue("telemetryEnabled")
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
                        "app_version": __version__,
                        "os_platform": platform.system().lower(),
                        "client_id": client_id,
                        "event": event,
                    }
                ).encode("utf-8")

                req = Request(
                    endpoint,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-telemetry-token": token,
                    },
                    method="POST",
                )
                with urlopen(req, timeout=5) as response:
                    settings.log(f'Telemetry: event "{event}" sent (status={response.getcode()} url={endpoint}).', Qgis.Info)
            except Exception as e:
                settings.log(f'Telemetry: failed to send event "{event}" ({e}).', Qgis.Warning)

        Thread(target=_send, daemon=True).start()
