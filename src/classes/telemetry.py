"""
Telemetry client for sharing anonymous usage data with the Riverscapes team. 
This helps us understand how our tools are used and prioritize improvements.
"""

from typing import Tuple
import os
import json
import uuid
import platform
from urllib.request import Request, urlopen
from threading import Thread
from .settings import Settings, MESSAGE_CATEGORY
from ...__version__ import __version__


class Telemetry:

    @staticmethod
    def _load_secrets() -> Tuple[str, str]:
        # secrets.json lives two directories above this file (at the plugin root)
        secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'secrets.json'))
        try:
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets = json.load(f)
            telemetry_cfg = secrets.get('telemetry', {})
            api_url = telemetry_cfg.get('api-url')
            api_token = telemetry_cfg.get('api-token')
            if api_url and api_token:
                endpoint = f'{api_url}/ingest/ping'
                token = api_token
                return endpoint, token
        except FileNotFoundError:
            pass  # silently disabled when secrets.json is absent
        except Exception:
            pass

        return None, None

    @staticmethod
    def get_client_id() -> str:
        # Check if a client ID already exists in settings, if not generate a new one and save it
        settings = Settings()
        client_id = settings.getValue('telemetryClientId')
        if not client_id:
            client_id = str(uuid.uuid4())
            settings.setValue('telemetryClientId', client_id)
        return client_id

    @staticmethod
    def send(event: str) -> None:
        """
        Send a telemetry ping in a background thread.
        Failures are silently ignored — telemetry must never break the app.
        """

        settings = Settings()
        app_name = MESSAGE_CATEGORY.replace(' ', '_')
        client_id = Telemetry.get_client_id()
        use_telemetry = settings.getValue('telemetryEnabled')
        endpoint, token = Telemetry._load_secrets()

        if use_telemetry is not True or not client_id or not endpoint or not token:
            return

        def _send():
            try:
                payload = json.dumps({
                    "app_name": app_name,
                    "app_version": __version__,
                    "os_platform": platform.system().lower(),
                    "client_id": client_id,
                    "event": event,
                }).encode("utf-8")

                req = Request(
                    endpoint,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-telemetry-token": token,
                    },
                    method="POST",
                )
                urlopen(req, timeout=5)
            except Exception:
                pass

        Thread(target=_send, daemon=True).start()
