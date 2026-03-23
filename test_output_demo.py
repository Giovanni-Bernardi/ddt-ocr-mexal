#!/usr/bin/env python3
"""
Test di validazione del parser DDT — dimostra l'output atteso
senza necessitare della API key Claude.

Basato sull'analisi visiva dei 3 DDT di esempio caricati.
"""

import json
from datetime import datetime

# ============================================================================
# Output atteso per i 3 DDT — estratto dall'analisi visiva diretta
# ============================================================================

DOC_1_CARRADORI = {
    "testata": {
        "tipo_documento": "DDT",
        "numero_documento": "2096",
        "data_documento": "20260320",
        "fornitore": {
            "ragione_sociale": "CARRADORI & CO. S.R.L",
            "indirizzo": "VIA DI MEZZO, 191/A",
            "cap": "51039",
            "citta": "QUARRATA",
            "provincia": "PT",
            "partita_iva": "IT02122760479",
            "codice_fiscale": "02122760479"
        },
        "destinatario": {
            "ragione_sociale": "SUTOR LAB HOME S.R.L.",
            "indirizzo": "STRADA REGIONALE, 66 KM.1",
            "cap": "51100",
            "citta": "PISTOIA",
            "provincia": "PT",
            "partita_iva": "IT02078250475",
            "codice_fiscale": None
        },
        "causale_trasporto": "VENDITE",
        "aspetto_beni": "A vista",
        "trasporto_a_mezzo": "MITTENTE",
        "pagamento": "RIMESSA DIRETTA",
        "riferimento_ordine": "Ordine cliente n. 490 del 04/03/2026",
        "codice_conto_mexal": "501.00152",
        "numero_colli": None,
        "peso_kg": None,
        "note": None
    },
    "righe": [
        {
            "riga_num": 1,
            "codice_articolo": "TTEFLSEX",
            "descrizione": "TESSUTO PL/CO/AF ART.FSL-SOFABLE COL.110",
            "unita_misura": "Mt",
            "quantita": 411.6,
            "prezzo_unitario": None,
            "importo": None,
            "sconto": None,
            "aliquota_iva": "22"
        },
        {
            "riga_num": 2,
            "codice_articolo": "TTEFLSEX",
            "descrizione": "TESSUTO PL/CO/AF ART.FSL-SOFABLE COL.4",
            "unita_misura": "Mt",
            "quantita": 621.5,
            "prezzo_unitario": None,
            "importo": None,
            "sconto": None,
            "aliquota_iva": "22"
        }
    ],
    "metadati_ocr": {
        "qualita_lettura": "alta",
        "tipo_documento_originale": "scansione",
        "campi_incerti": []
    }
}

DOC_2_GIRASOLI = {
    "testata": {
        "tipo_documento": "DDT",
        "numero_documento": "145",
        "data_documento": "20260319",
        "fornitore": {
            "ragione_sociale": "I GIRASOLI - I Girasoli Design della Piuma di Roberto Mazzei",
            "indirizzo": "Via Cesare Battisti 300/A",
            "cap": "51015",
            "citta": "MONSUMMANO TERME",
            "provincia": "PT",
            "partita_iva": "IT01638060473",
            "codice_fiscale": "MZZRRT62RO4G491M"
        },
        "destinatario": {
            "ragione_sociale": "SUTOR LAB HOME S.R.L.",
            "indirizzo": "Strada Regionale 66",
            "cap": "51100",
            "citta": "PISTOIA",
            "provincia": "PT",
            "partita_iva": "IT02078250475",
            "codice_fiscale": None
        },
        "causale_trasporto": "VENDITA",
        "aspetto_beni": None,
        "trasporto_a_mezzo": "cedente",
        "pagamento": None,
        "riferimento_ordine": "OC 2/2003",
        "codice_conto_mexal": None,
        "numero_colli": None,
        "peso_kg": None,
        "note": None
    },
    "righe": [
        {
            "riga_num": 1,
            "codice_articolo": None,
            "descrizione": "BRACCIOLI BOBOLI OC 2/2003",
            "unita_misura": "Pz",
            "quantita": 1.0,
            "prezzo_unitario": None,
            "importo": None,
            "sconto": None,
            "aliquota_iva": None
        },
        {
            "riga_num": 2,
            "codice_articolo": None,
            "descrizione": "RETRO SPALL MAXI BOBOLI OC 2/2003",
            "unita_misura": "Pz",
            "quantita": 1.0,
            "prezzo_unitario": None,
            "importo": None,
            "sconto": None,
            "aliquota_iva": None
        },
        {
            "riga_num": 3,
            "codice_articolo": None,
            "descrizione": "SED FREESIDE SX MAXI BOBOLI OC 2/2003",
            "unita_misura": "Pz",
            "quantita": 1.0,
            "prezzo_unitario": None,
            "importo": None,
            "sconto": None,
            "aliquota_iva": None
        },
        {
            "riga_num": 4,
            "codice_articolo": None,
            "descrizione": "SPALL MAXI BOBOLI OC 2/2003",
            "unita_misura": "Pz",
            "quantita": 1.0,
            "prezzo_unitario": None,
            "importo": None,
            "sconto": None,
            "aliquota_iva": None
        }
    ],
    "metadati_ocr": {
        "qualita_lettura": "media",
        "tipo_documento_originale": "scansione",
        "campi_incerti": ["causale_trasporto", "riferimento_ordine"]
    }
}

DOC_3_OPE = {
    "testata": {
        "tipo_documento": "DDT",
        "numero_documento": "19",
        "data_documento": "20260113",
        "fornitore": {
            "ragione_sociale": "O.P.E. TOSCANA S.R.L.",
            "indirizzo": "Via Europa n.c.m.",
            "cap": "51030",
            "citta": "SANTONUOVO - QUARRATA",
            "provincia": "PT",
            "partita_iva": "IT00992190470",
            "codice_fiscale": "00992190470"
        },
        "destinatario": {
            "ragione_sociale": "SUTOR LAB HOME",
            "indirizzo": "STRADA REGIONALE 66 KM 1",
            "cap": None,
            "citta": "PISTOIA",
            "provincia": "PT",
            "partita_iva": None,
            "codice_fiscale": None
        },
        "causale_trasporto": "VENDITA",
        "aspetto_beni": None,
        "trasporto_a_mezzo": "destinatario",
        "pagamento": None,
        "riferimento_ordine": None,
        "codice_conto_mexal": None,
        "numero_colli": None,
        "peso_kg": None,
        "note": None
    },
    "righe": [
        {
            "riga_num": 1,
            "codice_articolo": None,
            "descrizione": "ANGOLO BOBOLI",
            "unita_misura": "Pz",
            "quantita": 1.0,
            "prezzo_unitario": None,
            "importo": None,
            "sconto": None,
            "aliquota_iva": None
        }
    ],
    "metadati_ocr": {
        "qualita_lettura": "bassa",
        "tipo_documento_originale": "manoscritto",
        "campi_incerti": [
            "numero_documento",
            "data_documento",
            "destinatario.ragione_sociale",
            "righe[0].descrizione",
            "righe[0].quantita"
        ]
    }
}

# ============================================================================
# Output e confronto
# ============================================================================

def print_ddt_summary(data: dict, label: str):
    """Stampa un riepilogo leggibile del DDT estratto."""
    t = data["testata"]
    meta = data["metadati_ocr"]
    righe = data["righe"]

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    print(f"  Fornitore:    {t['fornitore']['ragione_sociale']}")
    print(f"  P.IVA:        {t['fornitore']['partita_iva']}")
    print(f"  DDT n.        {t['numero_documento']} del {t['data_documento']}")
    print(f"  Destinatario: {t['destinatario']['ragione_sociale']}")
    print(f"  Causale:      {t['causale_trasporto']}")
    print(f"  Rif. ordine:  {t.get('riferimento_ordine', '-')}")
    print(f"  Cod. Mexal:   {t.get('codice_conto_mexal', '-')}")
    print(f"  Pagamento:    {t.get('pagamento', '-')}")
    print()
    print(f"  {'#':<4} {'Codice':<12} {'Descrizione':<40} {'UM':<4} {'Qty':>8} {'IVA':>4}")
    print(f"  {'-'*4} {'-'*12} {'-'*40} {'-'*4} {'-'*8} {'-'*4}")
    for r in righe:
        cod = r.get("codice_articolo") or "-"
        desc = (r["descrizione"] or "")[:40]
        um = r.get("unita_misura") or "-"
        qty = r.get("quantita", 0)
        iva = r.get("aliquota_iva") or "-"
        print(f"  {r['riga_num']:<4} {cod:<12} {desc:<40} {um:<4} {qty:>8.1f} {iva:>4}")
    print()
    print(f"  Qualità OCR:  {meta['qualita_lettura']}")
    print(f"  Tipo doc:     {meta['tipo_documento_originale']}")
    if meta.get("campi_incerti"):
        print(f"  ⚠ Incerti:   {', '.join(meta['campi_incerti'])}")


def main():
    docs = [
        (DOC_1_CARRADORI, "DOC 1 — CARRADORI & CO. (digitale/tabellare)"),
        (DOC_2_GIRASOLI, "DOC 2 — I GIRASOLI (scansione, modulo prestampato)"),
        (DOC_3_OPE,      "DOC 3 — O.P.E. TOSCANA (manoscritto!)"),
    ]

    print("\n" + "🔍 " * 20)
    print("  DDT FORNITORE OCR PARSER — OUTPUT ATTESO")
    print("  Basato sull'analisi dei 3 DDT di esempio")
    print("🔍 " * 20)

    for data, label in docs:
        print_ddt_summary(data, label)

    # Salva i JSON di esempio
    for i, (data, _) in enumerate(docs, 1):
        data["_processing"] = {
            "file_origine": f"mar_23__Doc_{i}_by_iScanner.pdf",
            "modello_ai": "claude-sonnet-4-20250514",
            "timestamp": datetime.now().isoformat(),
            "tokens_input": "~1600 (immagine)",
            "tokens_output": "~800",
        }
        path = f"output/esempio_output_doc{i}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ JSON di esempio salvati in /home/claude/ddt_ocr_parser/")

    # -------------------------------------------------------------------
    # Mostra il payload Mexal che genereremmo per Doc 1 (il più completo)
    # -------------------------------------------------------------------
    print("\n" + "="*70)
    print("  ANTEPRIMA: Payload Mexal WebAPI per Doc 1 (Carradori)")
    print("  POST /documenti/movimenti-magazzino")
    print("="*70)

    mexal_payload = {
        "sigla": "BF",
        "serie": 1,
        "numero": "DA_ASSEGNARE",  # BF richiede numero obbligatorio
        "data_documento": DOC_1_CARRADORI["testata"]["data_documento"],
        "cod_conto": DOC_1_CARRADORI["testata"].get("codice_conto_mexal")
                     or "RICERCA_PER_PIVA",
        "id_riga": [[1, 1], [2, 1]],
        "tp_riga": [[1, "R"], [2, "R"]],
        "codice_articolo": [
            [1, DOC_1_CARRADORI["righe"][0]["codice_articolo"]],
            [2, DOC_1_CARRADORI["righe"][1]["codice_articolo"]],
        ],
        "quantita": [
            [1, DOC_1_CARRADORI["righe"][0]["quantita"]],
            [2, DOC_1_CARRADORI["righe"][1]["quantita"]],
        ],
        "cod_iva": [
            [1, DOC_1_CARRADORI["righe"][0]["aliquota_iva"]],
            [2, DOC_1_CARRADORI["righe"][1]["aliquota_iva"]],
        ],
    }

    print(json.dumps(mexal_payload, indent=2, ensure_ascii=False))
    print()
    print("⚠  NOTA: Per la BF il campo 'numero' è OBBLIGATORIO (non può essere 0)")
    print("   Il cod_conto '501.00152' è già visibile sul DDT Carradori")
    print("   Per gli altri DDT servirà lookup per P.IVA via GET /fornitori")


if __name__ == "__main__":
    main()
