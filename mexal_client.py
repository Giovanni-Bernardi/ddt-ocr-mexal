#!/usr/bin/env python3
"""
Mexal WebAPI Client — Fase 2 (v1.1)
=====================================
Client HTTP per le WebAPI Passepartout/Mexal con:
- Autenticazione Passepartout a doppio token (WebAPI + Gestionale)
- Retry automatico su errori 5xx
- Paginazione trasparente
- Lookup fornitore per P.IVA
- Creazione BF (Bolla Fornitore) da JSON OCR

Configurazione via variabili d'ambiente:
    export MEXAL_WEBAPI_USER="WEBAPI_ODOO"
    export MEXAL_WEBAPI_PASSWORD="Webapiodoo"
    export MEXAL_ADMIN_USER="admin"
    export MEXAL_ADMIN_PASSWORD="Mantellassi26"
    export MEXAL_DOMINIO="mantellassi"
    export MEXAL_AZIENDA="SOF"
    export MEXAL_ANNO="2024"
"""

import base64
import json
import logging
import os
import sys
import time
from typing import Optional

try:
    import requests
except ImportError:
    print("Installa requests: pip3 install requests")
    sys.exit(1)

logger = logging.getLogger("mexal_client")


class MexalClient:
    """Client per le WebAPI Passepartout/Mexal con doppio token auth."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        webapi_user: Optional[str] = None,
        webapi_password: Optional[str] = None,
        admin_user: Optional[str] = None,
        admin_password: Optional[str] = None,
        dominio: Optional[str] = None,
        azienda: Optional[str] = None,
        anno: Optional[str] = None,
    ):
        self.base_url = (
            base_url
            or os.environ.get("MEXAL_BASE_URL", "https://services.passepartout.cloud/webapi")
        )
        self.dominio = dominio or os.environ.get("MEXAL_DOMINIO", "mantellassi")
        self.azienda = azienda or os.environ.get("MEXAL_AZIENDA", "SOF")
        self.anno = anno or os.environ.get("MEXAL_ANNO", "2024")

        # Token 1: utente WebAPI
        wu = webapi_user or os.environ.get("MEXAL_WEBAPI_USER")
        wp = webapi_password or os.environ.get("MEXAL_WEBAPI_PASSWORD")
        # Token 2: utente gestionale
        au = admin_user or os.environ.get("MEXAL_ADMIN_USER")
        ap = admin_password or os.environ.get("MEXAL_ADMIN_PASSWORD")

        if not all([wu, wp, au, ap]):
            raise EnvironmentError(
                "Credenziali Mexal incomplete.\n"
                "Servono 4 variabili:\n"
                "  export MEXAL_WEBAPI_USER='WEBAPI_ODOO'\n"
                "  export MEXAL_WEBAPI_PASSWORD='...'\n"
                "  export MEXAL_ADMIN_USER='admin'\n"
                "  export MEXAL_ADMIN_PASSWORD='...'"
            )

        # Costruisci i due token base64
        token1 = base64.b64encode(f"{wu}:{wp}".encode()).decode()
        token2 = base64.b64encode(f"{au}:{ap}".encode()).decode()
        self._auth_header = f"Passepartout {token1} {token2} DOMINIO={self.dominio}"

        # Configurazione
        self.max_retries = 3
        self.retry_delay = 2
        self.page_size = 100
        self.timeout = 30

        # Session HTTP
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            "Coordinate-Gestionale": f"Azienda={self.azienda} Anno={self.anno}",
        })

        logger.info(
            "MexalClient inizializzato — %s Azienda=%s Anno=%s",
            self.base_url, self.azienda, self.anno,
        )

    # -----------------------------------------------------------------------
    # Metodi HTTP con retry
    # -----------------------------------------------------------------------

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Esegue una richiesta HTTP con retry automatico su errori 5xx."""
        kwargs.setdefault("timeout", self.timeout)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)

                logger.debug(
                    "%s %s → %d (%d bytes)",
                    method, url, response.status_code, len(response.content),
                )

                if response.status_code >= 500:
                    logger.warning(
                        "Errore server %d su %s (tentativo %d/%d)",
                        response.status_code, url, attempt, self.max_retries,
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay * attempt)
                        continue
                    response.raise_for_status()

                return response

            except requests.exceptions.Timeout:
                logger.warning("Timeout su %s (tentativo %d/%d)", url, attempt, self.max_retries)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                raise

            except requests.exceptions.ConnectionError as e:
                logger.error("Errore connessione a %s: %s", url, e)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                raise

        raise RuntimeError(f"Richiesta fallita dopo {self.max_retries} tentativi")

    def get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """GET su un endpoint risorse."""
        url = f"{self.base_url}/risorse/{endpoint}"
        response = self._request("GET", url, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict, params: Optional[dict] = None) -> requests.Response:
        """POST su un endpoint risorse. Restituisce la Response completa."""
        url = f"{self.base_url}/risorse/{endpoint}"
        response = self._request("POST", url, json=data, params=params)
        return response

    def search(self, endpoint: str, filtri: list) -> list:
        """POST ricerca con filtri + paginazione automatica."""
        url = f"{self.base_url}/risorse/{endpoint}/ricerca"
        all_results = []
        body = {"filtri": filtri}
        params = {"max": self.page_size}

        while True:
            response = self._request("POST", url, json=body, params=params)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                results = data.get("dati", data.get("risultati", []))
                if isinstance(results, list):
                    all_results.extend(results)
                next_token = data.get("next")
                if next_token:
                    params["next"] = next_token
                    logger.info("  Paginazione: totale finora %d", len(all_results))
                else:
                    break
            elif isinstance(data, list):
                all_results.extend(data)
                break
            else:
                break

        logger.info("Ricerca %s: %d risultati", endpoint, len(all_results))
        return all_results

    # -----------------------------------------------------------------------
    # Lookup fornitore per P.IVA
    # -----------------------------------------------------------------------

    def find_fornitore_by_piva(self, partita_iva: str) -> Optional[dict]:
        """Cerca un fornitore per P.IVA (senza prefisso IT)."""
        piva_clean = partita_iva.replace("IT", "").strip()
        logger.info("Ricerca fornitore per P.IVA: %s", piva_clean)

        results = self.search("fornitori", [
            {"campo": "partita_iva", "condizione": "=", "valore": piva_clean}
        ])

        if results:
            fornitore = results[0]
            logger.info(
                "  Trovato: %s (codice: %s)",
                fornitore.get("ragione_sociale", "?"),
                fornitore.get("codice", "?"),
            )
            return fornitore

        logger.warning("  Fornitore non trovato per P.IVA %s", piva_clean)
        return None

    # -----------------------------------------------------------------------
    # Lettura ultimo numero BF
    # -----------------------------------------------------------------------

    def get_ultimo_numero_bf(self, serie: int = 1) -> int:
        """Cerca l'ultimo numero BF per la serie specificata."""
        logger.info("Ricerca ultimo numero BF serie %d...", serie)
        try:
            results = self.search("documenti/movimenti-magazzino", [
                {"campo": "sigla", "condizione": "=", "valore": "BF"},
                {"campo": "serie", "condizione": "=", "valore": str(serie)},
            ])
            if not results:
                logger.info("  Nessuna BF trovata, parto da 0")
                return 0
            max_num = max(r.get("numero", 0) for r in results)
            logger.info("  Ultimo numero BF: %d", max_num)
            return max_num
        except Exception as e:
            logger.error("Errore ricerca ultimo BF: %s", e)
            return 0

    # -----------------------------------------------------------------------
    # Creazione BF da JSON OCR
    # -----------------------------------------------------------------------

    def crea_bf_da_ddt(
        self,
        ddt_data: dict,
        numero_bf: Optional[int] = None,
        serie: int = 1,
        cod_conto_override: Optional[str] = None,
        id_magazzino: int = 1,
        cod_iva_default: str = "22",
        dry_run: bool = False,
    ) -> dict:
        """
        Crea una BF in Mexal dal JSON OCR.

        Args:
            ddt_data: JSON dal parser OCR
            numero_bf: Numero BF (None = auto)
            serie: Serie documento
            cod_conto_override: Codice conto fornitore manuale
            id_magazzino: ID magazzino destinazione
            cod_iva_default: IVA default se non specificata
            dry_run: True = solo mostra payload, non invia
        """
        testata = ddt_data.get("testata", {})
        righe = ddt_data.get("righe", [])

        if not righe:
            return {"errore": "Nessuna riga articolo nel DDT"}

        # --- Determina cod_conto ---
        cod_conto = cod_conto_override or testata.get("codice_conto_mexal")

        if not cod_conto:
            piva = testata.get("fornitore", {}).get("partita_iva")
            if piva:
                fornitore = self.find_fornitore_by_piva(piva)
                if fornitore:
                    cod_conto = fornitore.get("codice")

        if not cod_conto:
            return {
                "errore": "Impossibile determinare il codice conto fornitore",
                "suggerimento": "Fornire cod_conto_override o verificare P.IVA in Mexal",
                "piva_cercata": testata.get("fornitore", {}).get("partita_iva"),
            }

        # --- Determina numero BF ---
        if numero_bf is None:
            ultimo = self.get_ultimo_numero_bf(serie)
            numero_bf = ultimo + 1
            logger.info("Numero BF auto-assegnato: %d", numero_bf)

        if numero_bf <= 0:
            return {"errore": "Il numero BF deve essere > 0"}

        # --- Costruisci payload ---
        payload = {
            "sigla": "BF",
            "serie": serie,
            "numero": numero_bf,
            "data_documento": testata.get("data_documento"),
            "cod_conto": cod_conto,
            "id_magazzino": id_magazzino,
            "id_riga": [],
            "tp_riga": [],
            "quantita": [],
            "cod_iva": [],
            "sigla_ordine": [],
            "serie_ordine": [],
            "numero_ordine": [],
            "sigla_doc_orig": [],
            "serie_doc_orig": [],
            "numero_doc_orig": [],
            "id_rif_testata": [],
        }

        codice_articolo = []
        descrizione_riga = []

        for i, riga in enumerate(righe, 1):
            payload["id_riga"].append([i, 1])
            payload["tp_riga"].append([i, "R"])
            payload["quantita"].append([i, riga.get("quantita", 0)])
            iva = riga.get("aliquota_iva") or cod_iva_default
            payload["cod_iva"].append([i, str(iva)])
            if riga.get("codice_articolo"):
                codice_articolo.append([i, riga["codice_articolo"]])
            if riga.get("descrizione"):
                descrizione_riga.append([i, riga["descrizione"]])

        if codice_articolo:
            payload["codice_articolo"] = codice_articolo
        if descrizione_riga:
            payload["descrizione_riga"] = descrizione_riga

        # --- Log ---
        logger.info("=" * 60)
        logger.info("Creazione BF %d/%d", serie, numero_bf)
        logger.info("  Fornitore: %s (%s)", testata.get("fornitore", {}).get("ragione_sociale"), cod_conto)
        logger.info("  Data: %s", testata.get("data_documento"))
        logger.info("  Righe: %d", len(righe))
        logger.info("=" * 60)

        if dry_run:
            logger.info("*** DRY RUN — payload NON inviato ***")
            return {
                "dry_run": True,
                "payload": payload,
                "endpoint": "POST /risorse/documenti/movimenti-magazzino",
            }

        # --- Invio ---
        logger.info("Invio POST a Mexal...")
        response = self.post("documenti/movimenti-magazzino", payload)

        if response.status_code == 201:
            location = response.headers.get("Location", "")
            logger.info("✅ BF creata! Location: %s", location)
            return {
                "successo": True,
                "numero_bf": numero_bf,
                "serie": serie,
                "location": location,
                "cod_conto": cod_conto,
            }
        else:
            error_body = {}
            try:
                error_body = response.json()
            except Exception:
                error_body = {"raw": response.text[:500]}
            logger.error("❌ Errore: HTTP %d — %s", response.status_code, json.dumps(error_body, ensure_ascii=False))
            return {
                "errore": f"HTTP {response.status_code}",
                "dettaglio": error_body,
                "payload_inviato": payload,
            }


# ===========================================================================
# Test connessione
# ===========================================================================

def test_connessione(client: MexalClient):
    """Testa la connessione leggendo il primo fornitore."""
    print("\n🔌 Test connessione Mexal...")
    try:
        data = client.get("fornitori", params={"max": 1})
        fornitori = data.get("dati", [])
        if fornitori:
            f = fornitori[0]
            print(f"  ✅ Connesso! Primo fornitore: {f.get('ragione_sociale')} ({f.get('codice')})")
            return True
        else:
            print("  ⚠️  Connesso ma nessun fornitore trovato")
            return True
    except Exception as e:
        print(f"  ❌ Errore connessione: {e}")
        return False


# ===========================================================================
# CLI
# ===========================================================================

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("Uso:")
        print("  python3 mexal_client.py --test              Testa la connessione")
        print("  python3 mexal_client.py <file.json> --dry-run   Mostra payload senza inviare")
        print("  python3 mexal_client.py <file.json>             Crea BF reale in Mexal")
        print()
        print("Variabili d'ambiente richieste:")
        print("  MEXAL_WEBAPI_USER      (es: WEBAPI_ODOO)")
        print("  MEXAL_WEBAPI_PASSWORD   (es: Webapiodoo)")
        print("  MEXAL_ADMIN_USER       (es: admin)")
        print("  MEXAL_ADMIN_PASSWORD    (es: xxxxxxxx)")
        sys.exit(1)

    # Test connessione
    if sys.argv[1] == "--test":
        client = MexalClient()
        test_connessione(client)
        return

    json_path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    with open(json_path, encoding="utf-8") as f:
        ddt_data = json.load(f)

    testata = ddt_data.get("testata", {})
    fornitore = testata.get("fornitore", {}).get("ragione_sociale", "?")
    num_ddt = testata.get("numero_documento", "?")

    print(f"\n{'='*60}")
    print(f"  Mexal BF Creator — {'DRY RUN' if dry_run else '🔴 LIVE'}")
    print(f"{'='*60}")
    print(f"  DDT: {json_path}")
    print(f"  Fornitore: {fornitore}")
    print(f"  DDT n. {num_ddt}")
    print(f"  Righe: {len(ddt_data.get('righe', []))}")
    print()

    if not dry_run:
        conferma = input("⚠️  Creerai una BF REALE in Mexal. Confermi? (si/no): ")
        if conferma.lower() not in ("si", "sì", "s", "yes", "y"):
            print("Annullato.")
            sys.exit(0)

    client = MexalClient()
    result = client.crea_bf_da_ddt(ddt_data, dry_run=dry_run)

    print(f"\n{'='*60}")
    print("  RISULTATO")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
