from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    MEALPREP_BASE_URL: str = ""

    # --- Kalender (nur lesend) ---
    #
    # Der Tagestyp ist die eine Wahrheit darueber, was fuer ein Tag heute ist
    # (Feiertag > Urlaub > Schule > Arbeit > Frei). fitness liest ihn, um an
    # einem Feiertag nicht denselben Plan als selbstverstaendlich hinzustellen.
    # Geschrieben wird dorthin nichts (Owner-Entscheid 2026-09-13).
    #
    # Leer heisst: die App verhaelt sich wie bisher und sagt nichts zum Tag.
    # Das ist auch der Zustand bei einem Selbsthoster ohne Kalender-Dienst.
    KALENDER_BASE_URL: str = ""
    KALENDER_FEED_TOKEN: str = ""
    KALENDER_TIMEOUT_SEC: int = 5

    # Multi-Tenant: sub aller Bestandsdaten + Fallback fuer headerlose interne Aufrufe.
    # Mandant fuer headerlose interne Aufrufer (life-ops, assets-api).
    #
    # ★ Leer als Vorbelegung, seit 2026-09-05. Vorher stand hier die Kennung
    # eines konkreten Menschen. Sie gehoert nicht in ein Repo, das
    # veroeffentlicht werden soll, und ein Selbsthoster hat ohnehin eine andere.
    # Wert kommt aus .env, eingetragen von
    # saganta/scripts/owner-kennung-eintragen.sh.
    #
    # Leer heisst fail-closed: headerlose Aufrufe sehen dann nichts, statt
    # stillschweigend die Daten irgendeines Kontos zu sehen. Beim Start wird
    # einmal gewarnt (app/main.py), damit der Zustand nicht unbemerkt bleibt.
    DEFAULT_OWNER_SUB: str = ""

    # Native Apps: HS256-Backend-JWT (aud=fitness-api) vom saganta-auth-service.
    # Muss == SAGANTA_BACKEND_SECRET des auth-service sein (Wert NUR in der .env des Wirts).
    # Leer => Bearer-Auth deaktiviert (nur Header/Default-Pfad, bisheriges Verhalten).
    SAGANTA_BACKEND_SECRET: str = ""

    # F1: Admin-Endpunkte (/api/admin/export|import) verlangen dieses Token als
    # X-Admin-Token-Header. Leer = fail-closed (Admin-Routen gesperrt).
    ADMIN_TOKEN: str = ""

    # Echtheitsnachweis fuer den X-Saganta-Sub-Header (app/tenant_auth.py).
    # Eigenes Geheimnis je Dienst. Leer => bisheriges Verhalten, Header gilt
    # ungeprueft. TENANT_HEADER_ENFORCE: 0 = beobachten, 1 = 401 erzwingen.
    # Erst scharf schalten, wenn die Protokolle ueber Tage still bleiben.
    FITNESS_TENANT_SECRET: str = ""
    TENANT_HEADER_ENFORCE: int = 0

    # Geheimnis fuer die Mandanten-Signatur BEIM AUFRUF von MealPrep
    # (X-Saganta-Sub-Sig). Das ist das Geheimnis von MealPrep, nicht das
    # eigene: hier sind wir der Absender. Leer = Header ohne Signatur, was
    # MealPrep in seiner Beobachtungsphase noch annimmt.
    MEALPREP_TENANT_SECRET: str = ""

    # --- Benachrichtigungskanal (optional) ---
    #
    # ★ Bewusst abschaltbar und leer als Vorbelegung. Saganta soll
    # eigenstaendig laufen und wird veroeffentlicht: ein Selbsthoster hat
    # keinen brain-bus und kein Mosquitto. Leer heisst, der Dienst meldet
    # nichts nach draussen und funktioniert im Uebrigen unveraendert.
    # Im Haus traegt der bestehende Broker-Nutzer (wie alerts, briefkasten),
    # es braucht keinen eigenen.
    MQTT_HOST: str = ""
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_PASSWORD_FILE: str = ""

    # Token fuer POST /api/anstoss/pruefen. Der Endpunkt arbeitet ueber ALLE
    # Mandanten und ist damit ein Verwaltungsvorgang. Leer = fail-closed.
    ANSTOSS_TOKEN: str = ""

    def mqtt_passwort(self) -> str:
        """Passwort aus der Datei, sonst aus der Umgebung.

        Die Datei ist der Weg im Haus (Docker-Secret, read-only gemountet).
        Sie wird bei jedem Verbindungsaufbau gelesen und nicht zwischen-
        gespeichert, damit eine Rotation ohne Neustart des Dienstes wirkt.
        """
        if self.MQTT_PASSWORD_FILE:
            try:
                with open(self.MQTT_PASSWORD_FILE, encoding="utf-8") as f:
                    return f.read().strip()
            except OSError:
                return self.MQTT_PASSWORD
        return self.MQTT_PASSWORD

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
