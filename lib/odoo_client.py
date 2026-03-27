"""Client Odoo JSON-RPC — autenticazione e lettura lead CRM."""

import re
import requests
from typing import Optional

from lib.ui_common import get_secret


class OdooClient:
    """Client per Odoo via JSON-RPC con sessione cookie."""

    def __init__(self):
        self.url = get_secret("ODOO_URL", "https://odoo.mantellassi.com")
        self._db = get_secret("ODOO_DB", "odoo.mantellassi.com")
        self._username = get_secret("ODOO_USERNAME")
        self._password = get_secret("ODOO_PASSWORD")
        self._session: Optional[requests.Session] = None
        self._uid: Optional[int] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._username and self._password)

    def authenticate(self) -> bool:
        """Autentica e salva la sessione cookie. Ritorna True se OK."""
        self._session = requests.Session()
        resp = self._session.post(
            f"{self.url}/web/session/authenticate",
            json={
                "jsonrpc": "2.0",
                "params": {
                    "db": self._db,
                    "login": self._username,
                    "password": self._password,
                },
            },
            timeout=15,
        )
        data = resp.json()
        result = data.get("result", {})
        self._uid = result.get("uid")
        if not self._uid:
            error = data.get("error", {})
            raise ConnectionError(
                error.get("message", "Autenticazione Odoo fallita — verifica credenziali")
            )
        return True

    def _call_kw(self, model: str, method: str, args: list, kwargs: Optional[dict] = None) -> list:
        """Chiamata generica JSON-RPC call_kw."""
        if not self._session:
            self.authenticate()
        resp = self._session.post(
            f"{self.url}/web/dataset/call_kw",
            json={
                "jsonrpc": "2.0",
                "params": {
                    "model": model,
                    "method": method,
                    "args": args,
                    "kwargs": kwargs or {},
                },
            },
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            err = data["error"]
            raise RuntimeError(err.get("message", str(err)))
        return data.get("result", [])

    def get_won_leads(self, limit: int = 50) -> list[dict]:
        """Legge i lead CRM con stage 'Won' (stage_id=4)."""
        return self._call_kw(
            "crm.lead",
            "search_read",
            [[[
                ["stage_id", "=", 4],
                ["type", "=", "opportunity"],
            ]]],
            {
                "fields": [
                    "name", "partner_name", "contact_name", "email_from",
                    "phone", "street", "city", "zip", "state_id",
                    "country_id", "partner_id", "stage_id", "date_closed",
                    "user_id",
                ],
                "limit": limit,
                "order": "date_closed desc",
            },
        )

    def get_partner(self, partner_id: int) -> Optional[dict]:
        """Legge dettagli partner (per CF e P.IVA)."""
        results = self._call_kw(
            "res.partner",
            "read",
            [[partner_id]],
            {
                "fields": [
                    "name", "email", "phone", "street", "city", "zip",
                    "state_id", "country_id", "vat", "l10n_it_codice_fiscale",
                    "company_type",
                ],
            },
        )
        return results[0] if results else None


def extract_provincia(state_id) -> str:
    """Estrae la sigla provincia da state_id Odoo.

    state_id può essere:
    - [id, "Firenze (IT)"] → "FI" (non disponibile, usiamo mapping)
    - [id, "Pistoia"] → "PT"
    - False/None → ""
    """
    if not state_id or state_id is False:
        return ""
    if isinstance(state_id, (list, tuple)) and len(state_id) >= 2:
        name = str(state_id[1])
    else:
        name = str(state_id)

    # Cerca sigla tra parentesi: "Firenze (FI)" → "FI"
    m = re.search(r'\(([A-Z]{2})\)', name)
    if m:
        return m.group(1)

    # Mapping città principali → sigla
    mapping = {
        "firenze": "FI", "milano": "MI", "roma": "RM", "torino": "TO",
        "napoli": "NA", "bologna": "BO", "genova": "GE", "venezia": "VE",
        "pistoia": "PT", "prato": "PO", "lucca": "LU", "pisa": "PI",
        "livorno": "LI", "arezzo": "AR", "siena": "SI", "grosseto": "GR",
        "massa-carrara": "MS", "massa": "MS", "carrara": "MS",
        "bergamo": "BG", "brescia": "BS", "como": "CO", "cremona": "CR",
        "lecco": "LC", "lodi": "LO", "mantova": "MN", "monza": "MB",
        "pavia": "PV", "sondrio": "SO", "varese": "VA",
        "padova": "PD", "verona": "VR", "vicenza": "VI", "treviso": "TV",
        "belluno": "BL", "rovigo": "RO",
        "bari": "BA", "palermo": "PA", "catania": "CT", "messina": "ME",
        "perugia": "PG", "terni": "TR", "ancona": "AN", "pesaro": "PU",
        "cagliari": "CA", "sassari": "SS",
        "trento": "TN", "bolzano": "BZ", "aosta": "AO",
        "trieste": "TS", "udine": "UD", "gorizia": "GO", "pordenone": "PN",
        "parma": "PR", "modena": "MO", "reggio emilia": "RE", "ferrara": "FE",
        "ravenna": "RA", "forlì-cesena": "FC", "rimini": "RN", "piacenza": "PC",
    }
    name_lower = name.lower().strip()
    return mapping.get(name_lower, "")


def normalize_vat(vat) -> str:
    """Normalizza P.IVA Odoo → formato Mexal (senza prefisso IT)."""
    if not vat or vat is False:
        return ""
    s = str(vat).strip()
    if s.upper().startswith("IT"):
        s = s[2:]
    return s
