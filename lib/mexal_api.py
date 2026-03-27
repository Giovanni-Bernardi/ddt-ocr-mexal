"""Client API Mexal condiviso — autenticazione, ricerche, creazione documenti.

Gestisce DUE aziende:
- SOF per anagrafiche (clienti, fornitori)
- SUT per documenti (OC, BF) e articoli
"""

import base64
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from lib.ui_common import get_secret

MAX_RETRIES = 3
RETRY_BASE_DELAY = 3

# Aziende
AZ_DOCUMENTI = "SUT"   # OC, BF, articoli
AZ_ANAGRAFICHE = "SOF"  # clienti, fornitori


class MexalClient:
    """Client per WebAPI Mexal/Passepartout con supporto doppia azienda."""

    def __init__(self):
        self.base_url = get_secret("MEXAL_BASE_URL", "https://services.passepartout.cloud/webapi")
        self._webapi_user = get_secret("MEXAL_WEBAPI_USER", "WEBAPI_ODOO")
        self._webapi_pwd = get_secret("MEXAL_WEBAPI_PASSWORD")
        self._admin_user = get_secret("MEXAL_ADMIN_USER", "admin")
        self._admin_pwd = get_secret("MEXAL_ADMIN_PASSWORD")
        self._dominio = get_secret("MEXAL_DOMINIO", "mantellassi")
        self._anno = get_secret("MEXAL_ANNO", "2026")

    def headers(self, azienda: Optional[str] = None) -> dict:
        """Costruisce gli header Mexal. azienda default = SUT."""
        az = azienda or AZ_DOCUMENTI
        token1 = base64.b64encode(f"{self._webapi_user}:{self._webapi_pwd}".encode()).decode()
        token2 = base64.b64encode(f"{self._admin_user}:{self._admin_pwd}".encode()).decode()
        return {
            "Authorization": f"Passepartout {token1} {token2} DOMINIO={self._dominio}",
            "Content-Type": "application/json",
            "Coordinate-Gestionale": f"Azienda={az} Anno={self._anno}",
        }

    def _session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BASE_DELAY,
            status_forcelist=[429, 500, 502, 503, 529],
            allowed_methods=["GET", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get(self, path: str, params: Optional[dict] = None, timeout: int = 15,
             azienda: Optional[str] = None):
        return self._session().get(f"{self.base_url}{path}",
                                   headers=self.headers(azienda), params=params, timeout=timeout)

    def _post(self, path: str, json_data: dict, params: Optional[dict] = None,
              timeout: int = 15, azienda: Optional[str] = None):
        return self._session().post(f"{self.base_url}{path}",
                                    headers=self.headers(azienda), json=json_data,
                                    params=params, timeout=timeout)

    def _delete(self, path: str, timeout: int = 15, azienda: Optional[str] = None):
        return self._session().delete(f"{self.base_url}{path}",
                                      headers=self.headers(azienda), timeout=timeout)

    # -----------------------------------------------------------------------
    # Fornitori (azienda SOF)
    # -----------------------------------------------------------------------
    def search_fornitore_by_piva(self, partita_iva: str) -> Optional[dict]:
        piva = partita_iva.replace("IT", "").strip()
        resp = self._post("/risorse/fornitori/ricerca",
                          {"filtri": [{"campo": "partita_iva", "condizione": "=", "valore": piva}]},
                          azienda=AZ_ANAGRAFICHE)
        if resp.status_code == 200:
            dati = resp.json().get("dati", [])
            return dati[0] if dati else None
        return None

    def search_fornitore_by_nome(self, testo: str, max_results: int = 50) -> list[dict]:
        resp = self._post("/risorse/fornitori/ricerca",
                          {"filtri": [{"campo": "ragione_sociale", "condizione": "contiene",
                                       "case_insensitive": True, "valore": testo.strip()}]},
                          params={"max": max_results}, azienda=AZ_ANAGRAFICHE)
        if resp.status_code == 200:
            return resp.json().get("dati", [])
        return []

    def list_fornitori(self, max_results: int = 50) -> list[dict]:
        resp = self._get("/risorse/fornitori", params={"max": max_results}, azienda=AZ_ANAGRAFICHE)
        if resp.status_code == 200:
            return resp.json().get("dati", [])
        return []

    def get_fornitore(self, codice: str) -> Optional[dict]:
        resp = self._get(f"/risorse/fornitori/{codice}", azienda=AZ_ANAGRAFICHE)
        if resp.status_code == 200:
            return resp.json()
        return None

    # -----------------------------------------------------------------------
    # Clienti (azienda SOF)
    # -----------------------------------------------------------------------
    def search_clienti(self, campo: str, valore: str, condizione: str = "contiene",
                       max_results: int = 50) -> list[dict]:
        resp = self._post("/risorse/clienti/ricerca",
                          {"filtri": [{"campo": campo, "condizione": condizione,
                                       "case_insensitive": True, "valore": valore.strip()}]},
                          params={"max": max_results}, azienda=AZ_ANAGRAFICHE)
        if resp.status_code == 200:
            return resp.json().get("dati", [])
        return []

    def get_cliente(self, codice: str) -> Optional[dict]:
        resp = self._get(f"/risorse/clienti/{codice}", azienda=AZ_ANAGRAFICHE)
        if resp.status_code == 200:
            return resp.json()
        return None

    def crea_cliente(self, payload: dict) -> dict:
        resp = self._post("/risorse/clienti", payload, timeout=30, azienda=AZ_ANAGRAFICHE)
        if resp.status_code == 201:
            return {"successo": True, "location": resp.headers.get("Location", "")}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    def elimina_cliente(self, codice: str) -> dict:
        resp = self._delete(f"/risorse/clienti/{codice}", azienda=AZ_ANAGRAFICHE)
        if resp.status_code in (200, 204):
            return {"successo": True}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    # -----------------------------------------------------------------------
    # Articoli (azienda SUT)
    # -----------------------------------------------------------------------
    def search_articoli(self, testo: str, campo: str = "descrizione",
                        max_results: int = 20) -> list[dict]:
        session = self._session()

        def _do(query: str) -> list[dict]:
            resp = session.post(
                f"{self.base_url}/risorse/articoli/ricerca?max={max_results}",
                headers=self.headers(AZ_DOCUMENTI),
                json={"filtri": [{"campo": campo, "condizione": "contiene",
                                  "case_insensitive": True, "valore": query.strip()}]},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get("dati", [])
            return []

        risultati = _do(testo)
        if risultati:
            return risultati
        parole = [p for p in testo.strip().split() if len(p) >= 3]
        if parole and parole[0].strip() != testo.strip():
            risultati = _do(parole[0])
        return risultati

    def get_articolo(self, codice: str) -> Optional[dict]:
        resp = self._get(f"/risorse/articoli/{codice}", azienda=AZ_DOCUMENTI)
        if resp.status_code == 200:
            return resp.json()
        return None

    def crea_articolo(self, payload: dict) -> dict:
        resp = self._post("/risorse/articoli", payload, timeout=30, azienda=AZ_DOCUMENTI)
        if resp.status_code == 201:
            return {"successo": True, "location": resp.headers.get("Location", "")}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    # -----------------------------------------------------------------------
    # Documenti (azienda SUT)
    # -----------------------------------------------------------------------
    def crea_bf(self, payload: dict) -> dict:
        resp = self._post("/risorse/documenti/movimenti-magazzino", payload,
                          timeout=30, azienda=AZ_DOCUMENTI)
        if resp.status_code == 201:
            return {"successo": True, "location": resp.headers.get("Location", "")}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    def crea_oc(self, payload: dict) -> dict:
        resp = self._post("/risorse/documenti/ordini-clienti", payload,
                          timeout=30, azienda=AZ_DOCUMENTI)
        if resp.status_code == 201:
            return {"successo": True, "location": resp.headers.get("Location", "")}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    def elimina_oc(self, serie: int, numero: int) -> dict:
        resp = self._delete(f"/risorse/documenti/ordini-clienti/OC+{serie}+{numero}",
                            azienda=AZ_DOCUMENTI)
        if resp.status_code in (200, 204):
            return {"successo": True}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    def elimina_bf(self, serie: int, numero: int) -> dict:
        resp = self._delete(f"/risorse/documenti/movimenti-magazzino/BF+{serie}+{numero}",
                            azienda=AZ_DOCUMENTI)
        if resp.status_code in (200, 204):
            return {"successo": True}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    def crea_of(self, payload: dict) -> dict:
        resp = self._post("/risorse/documenti/ordini-fornitori", payload,
                          timeout=30, azienda=AZ_DOCUMENTI)
        if resp.status_code == 201:
            return {"successo": True, "location": resp.headers.get("Location", "")}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    def elimina_of(self, serie: int, numero: int) -> dict:
        resp = self._delete(f"/risorse/documenti/ordini-fornitori/OF+{serie}+{numero}",
                            azienda=AZ_DOCUMENTI)
        if resp.status_code in (200, 204):
            return {"successo": True}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}

    # -----------------------------------------------------------------------
    # Servizi (azienda SUT)
    # -----------------------------------------------------------------------
    def sviluppo_distinta_base(self, codice_articolo: str, quantita: float = 1,
                                id_riga_oc: int = 0, data_documento: str = "",
                                codice_cliente: str = "") -> dict:
        """Sviluppo distinta base. id_riga_oc=0 = simulazione."""
        from datetime import datetime
        if not data_documento:
            data_documento = datetime.now().strftime("%Y%m%d")
        payload = {
            "cmd": "sviluppo_distinta_base",
            "dati": {
                "codice_articolo": codice_articolo,
                "codice_art_padre": "",
                "codice_cliente": codice_cliente,
                "data_documento": data_documento,
                "codice": 0,
                "cod_sottobolla": 0,
                "nr_rif_pf": 0,
                "id_riga_oc": id_riga_oc,
                "quantita_taglie": [[1, quantita]],
            },
        }
        resp = self._post("/servizi", payload, timeout=30, azienda=AZ_DOCUMENTI)
        if resp.status_code == 200:
            return {"successo": True, "dati": resp.json()}
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}
