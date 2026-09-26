"""MQTT-Publisher, damit der Dienst seine Ereignisse selbst meldet.

Uebernommen aus ``alerts/app/mqtt.py`` (dem Baustein des service-template) mit
demselben Topic-Schema:

    homelab/{dienst}/{gegenstand}/{vorgang}

★ Der Docstring dieses Bausteins nennt seit Jahren ``homelab/fitness/workout/
completed`` als Beispiel. Die Fitness-App war als Producer vorgesehen und ist
bis 2026-09-12 nie einer geworden. Stattdessen stand daneben ein Bash-Skript,
das die App von aussen abfragte und die Nutzlast mit Zeichenkettenersetzung in
Python-Quelltext zusammenbaute. Ein Uebungsname mit drei Anfuehrungszeichen
darin fuehrte dort beliebigen Code aus. Der Weg von innen hat dieses Problem
strukturell nicht: hier wird eine Datenstruktur serialisiert, kein Quelltext
gebaut.

Nachsicht ist Absicht, aber nicht stumm: ein nicht erreichbarer Broker darf
die Erfassung im Gym nicht behindern, deshalb faengt ``publish`` den Fehler.
Damit das nicht wieder jahrelang unbemerkt bleibt, zaehlt der Publisher seine
Fehlschlaege, und ``/health`` gibt den Stand aus.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

TOPIC_PREFIX = "homelab"


def topic(entity: str, action: str) -> str:
    return f"{TOPIC_PREFIX}/fitness/{entity}/{action}"


class MqttPublisher:
    def __init__(self) -> None:
        self._client: Any | None = None
        self.versuche = 0
        self.fehler = 0
        self.letzter_fehler: str | None = None

    @property
    def konfiguriert(self) -> bool:
        return bool(settings.MQTT_HOST)

    def zustand(self) -> dict:
        return {
            "konfiguriert": self.konfiguriert,
            "verbunden": self._client is not None,
            "versuche": self.versuche,
            "fehler": self.fehler,
            "letzter_fehler": self.letzter_fehler,
        }

    def _verbinden(self) -> None:
        if self._client is not None:
            return
        # Import erst hier: ohne eingerichteten Broker soll die App auch ohne
        # die Abhaengigkeit starten koennen.
        import paho.mqtt.client as mqtt

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="fitness-publisher",
        )
        if settings.MQTT_USERNAME:
            client.username_pw_set(settings.MQTT_USERNAME, settings.mqtt_passwort())
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=60)
        client.loop_start()
        self._client = client
        logger.info("MQTT verbunden (%s:%s)", settings.MQTT_HOST, settings.MQTT_PORT)

    def trennen(self) -> None:
        if self._client is None:
            return
        try:
            self._client.loop_stop()
            self._client.disconnect()
        finally:
            self._client = None

    def publish(self, entity: str, action: str, payload: dict[str, Any]) -> bool:
        """Ereignis melden. Gibt zurueck, ob es den Broker erreicht hat."""
        if not self.konfiguriert:
            return False
        self.versuche += 1
        ziel = topic(entity, action)
        try:
            self._verbinden()
            ergebnis = self._client.publish(ziel, json.dumps(payload, default=str), qos=1)
            # rc 0 heisst angenommen. Ein spaeterer Verbindungsabbruch faellt
            # beim naechsten Lauf auf, dafuer ist der Zaehler da.
            if ergebnis.rc != 0:
                raise RuntimeError(f"Broker lehnte ab (rc={ergebnis.rc})")
            self.letzter_fehler = None
            return True
        except Exception as fehler:
            self.fehler += 1
            self.letzter_fehler = f"{ziel}: {fehler}"
            # Verbindung verwerfen, damit der naechste Versuch neu aufbaut.
            self._client = None
            logger.warning("MQTT-Meldung fehlgeschlagen (%s)", ziel, exc_info=True)
            return False


publisher = MqttPublisher()
