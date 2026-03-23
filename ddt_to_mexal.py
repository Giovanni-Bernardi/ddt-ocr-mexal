#!/usr/bin/env python3
"""
DDT → Mexal BF Payload Builder
================================
Converte l'output JSON del parser OCR nel payload per la creazione
di una Bolla Fornitore (BF) via Mexal WebAPI.

Gestisce:
- Costruzione payload con formato array Mexal [[indice, valore], ...]
- Lookup fornitore per P.IVA (quando cod_conto non è nel DDT)
- Validazione campi obbligatori
- Generazione numero BF progressivo
"""

import json
import logging
from typing import Optional

logger = logging.getLogger("ddt_to_mexal")


class DDTtoMexalConverter:
    """
    Converte i dati estratti da un DDT nel payload JSON per la creazione
    di una BF (Bolla Fornitore) sull'endpoint:
    POST /documenti/movimenti-magazzino
    """

    def __init__(self, ddt_data: dict):
        self.ddt = ddt_data
        self.testata = ddt_data.get("testata", {})
        self.righe = ddt_data.get("righe", [])
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """
        Verifica che i dati minimi per creare una BF siano presenti.
        Restituisce True se il DDT è processabile.
        """
        self.errors = []
        self.warnings = []

        # Campi obbligatori testata
        if not self.testata.get("data_documento"):
            self.errors.append("Data documento mancante")

        if not self.testata.get("fornitore", {}).get("partita_iva"):
            if not self.testata.get("codice_conto_mexal"):
                self.errors.append(
                    "Né P.IVA fornitore né codice conto Mexal disponibili — "
                    "impossibile identificare il fornitore"
                )

        # Righe obbligatorie
        if not self.righe:
            self.errors.append("Nessuna riga articolo estratta")

        for i, riga in enumerate(self.righe, 1):
            if not riga.get("quantita") or riga["quantita"] <= 0:
                self.errors.append(f"Riga {i}: quantità mancante o zero")

            if not riga.get("descrizione"):
                self.errors.append(f"Riga {i}: descrizione mancante")

            # Warnings (non bloccanti)
            if not riga.get("codice_articolo"):
                self.warnings.append(
                    f"Riga {i}: codice articolo mancante — "
                    f"servirà matching manuale (desc: '{riga.get('descrizione', '')}')"
                )
            if not riga.get("aliquota_iva"):
                self.warnings.append(
                    f"Riga {i}: aliquota IVA non specificata — verrà usato default"
                )

        # Metadati OCR
        meta = self.ddt.get("metadati_ocr", {})
        if meta.get("qualita_lettura") == "bassa":
            self.warnings.append(
                "Qualità OCR bassa — revisione manuale fortemente consigliata"
            )
        if meta.get("campi_incerti"):
            self.warnings.append(
                f"Campi con lettura incerta: {', '.join(meta['campi_incerti'])}"
            )

        return len(self.errors) == 0

    def build_payload(
        self,
        numero_bf: int,
        serie: int = 1,
        cod_conto_override: Optional[str] = None,
        id_magazzino: int = 1,
        cod_iva_default: str = "22",
    ) -> dict:
        """
        Costruisce il payload JSON per:
        POST https://services.passepartout.cloud/webapi/risorse/documenti/movimenti-magazzino

        Args:
            numero_bf: Numero BF (obbligatorio, non può essere 0)
            serie: Serie documento (default 1)
            cod_conto_override: Codice conto fornitore Mexal (se non nel DDT)
            id_magazzino: ID magazzino destinazione
            cod_iva_default: Aliquota IVA di default quando non specificata

        Returns:
            dict: Payload pronto per il POST
        """
        if numero_bf <= 0:
            raise ValueError("Il numero BF è obbligatorio e deve essere > 0")

        # Determina il codice conto
        cod_conto = (
            cod_conto_override
            or self.testata.get("codice_conto_mexal")
        )
        if not cod_conto:
            raise ValueError(
                "Codice conto Mexal non determinato. "
                "Fornisci cod_conto_override o usa lookup per P.IVA: "
                f"{self.testata.get('fornitore', {}).get('partita_iva', '?')}"
            )

        payload = {
            "sigla": "BF",
            "serie": serie,
            "numero": numero_bf,
            "data_documento": self.testata["data_documento"],
            "cod_conto": cod_conto,
            "id_magazzino": id_magazzino,
        }

        # Costruisci array righe nel formato Mexal: [[indice, valore], ...]
        id_riga = []
        tp_riga = []
        codice_articolo = []
        quantita = []
        cod_iva = []
        # Campi opzionali
        descrizione_riga = []

        for i, riga in enumerate(self.righe, 1):
            id_riga.append([i, 1])          # 1 = prima testata (singola)
            tp_riga.append([i, "R"])         # R = riga merce

            if riga.get("codice_articolo"):
                codice_articolo.append([i, riga["codice_articolo"]])

            quantita.append([i, riga["quantita"]])

            iva = riga.get("aliquota_iva") or cod_iva_default
            cod_iva.append([i, str(iva)])

            if riga.get("descrizione"):
                descrizione_riga.append([i, riga["descrizione"]])

        payload["id_riga"] = id_riga
        payload["tp_riga"] = tp_riga
        payload["quantita"] = quantita
        payload["cod_iva"] = cod_iva

        if codice_articolo:
            payload["codice_articolo"] = codice_articolo

        if descrizione_riga:
            payload["descrizione_riga"] = descrizione_riga

        return payload

    def build_api_request(
        self,
        numero_bf: int,
        base_url: str = "https://services.passepartout.cloud/webapi",
        **kwargs,
    ) -> dict:
        """
        Restituisce la specifica completa della chiamata API:
        metodo, URL, headers, body.
        """
        payload = self.build_payload(numero_bf, **kwargs)

        return {
            "method": "POST",
            "url": f"{base_url}/risorse/documenti/movimenti-magazzino",
            "headers": {
                "Authorization": "Passepartout <base64(user:password)> DOMINIO=mantellassi",
                "Content-Type": "application/json",
                "Coordinate-Gestionale": "Azienda=SOF Anno=2024",
            },
            "body": payload,
            "note": (
                "Il campo Authorization va compilato con le credenziali reali. "
                "Il numero BF deve essere univoco e non già esistente."
            ),
        }

    def get_report(self) -> str:
        """Genera un report leggibile della conversione."""
        lines = []
        lines.append(f"Fornitore: {self.testata.get('fornitore', {}).get('ragione_sociale', '?')}")
        lines.append(f"DDT n. {self.testata.get('numero_documento', '?')} "
                      f"del {self.testata.get('data_documento', '?')}")
        lines.append(f"Righe: {len(self.righe)}")
        lines.append(f"Cod. conto Mexal: {self.testata.get('codice_conto_mexal', 'DA CERCARE')}")

        if self.errors:
            lines.append(f"\n❌ ERRORI ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"   • {e}")

        if self.warnings:
            lines.append(f"\n⚠️  AVVISI ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"   • {w}")

        return "\n".join(lines)


# ============================================================================
# Demo con i DDT di esempio
# ============================================================================

def demo():
    """Dimostra la conversione con i 3 DDT di esempio."""
    import os

    example_dir = os.path.dirname(os.path.abspath(__file__))

    for i in range(1, 4):
        json_path = os.path.join(example_dir, f"esempio_output_doc{i}.json")
        if not os.path.exists(json_path):
            print(f"⚠ File non trovato: {json_path}")
            print("  Esegui prima test_output_demo.py per generare i JSON di esempio")
            return

        with open(json_path) as f:
            ddt_data = json.load(f)

        converter = DDTtoMexalConverter(ddt_data)
        is_valid = converter.validate()

        print(f"\n{'='*60}")
        print(f"  Doc {i} — Conversione DDT → BF Mexal")
        print(f"{'='*60}")
        print(converter.get_report())

        if is_valid:
            try:
                # Per il doc 1 abbiamo il cod_conto, per gli altri simuliamo
                if i == 1:
                    api_req = converter.build_api_request(numero_bf=100 + i)
                else:
                    api_req = converter.build_api_request(
                        numero_bf=100 + i,
                        cod_conto_override="601.00001",  # placeholder
                    )
                print(f"\n✅ Payload generato ({api_req['method']} {api_req['url']})")
                print(json.dumps(api_req["body"], indent=2, ensure_ascii=False))
            except ValueError as e:
                print(f"\n❌ Impossibile generare payload: {e}")
        else:
            print("\n❌ DDT non processabile — correggere gli errori prima")


if __name__ == "__main__":
    demo()
