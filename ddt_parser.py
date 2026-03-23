#!/usr/bin/env python3
"""
DDT Fornitore OCR Parser — Fase 1 (v1.1)
==========================================
Script standalone per estrarre dati strutturati da DDT fornitore (PDF scansionati)
usando Claude API come motore OCR + parser intelligente.

v1.1 — Miglioramenti prompt:
  - Fix prefisso IT su P.IVA
  - Estrazione provincia da CAP/indirizzo
  - Estrazione riferimento ordine dalle righe articolo
  - Migliore gestione quantità su documenti manoscritti

Uso:
    python ddt_parser.py /percorso/al/ddt.pdf
    python ddt_parser.py /percorso/cartella/  (processa tutti i PDF nella cartella)

Requisiti:
    pip install anthropic Pillow

Configurazione:
    export ANTHROPIC_API_KEY="sk-ant-..."

Output:
    Per ogni PDF genera un file JSON con i dati estratti nella stessa cartella.
"""

import anthropic
import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ddt_parser")

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
IMAGE_DPI = 200  # Risoluzione per la rasterizzazione — 200 DPI è un buon compromesso

# ---------------------------------------------------------------------------
# Prompt di sistema per l'estrazione DDT (v1.1)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
Sei un esperto contabile italiano specializzato nella lettura di Documenti di Trasporto (DDT).
Il tuo compito è estrarre tutti i dati strutturati da un'immagine di DDT fornitore.

REGOLE IMPORTANTI:
- Estrai ESATTAMENTE ciò che vedi, non inventare dati mancanti
- Per i campi non presenti o illeggibili, usa null
- Le quantità devono essere numeri (usa il punto come separatore decimale: 411,6 → 411.6)
- Le date devono essere in formato YYYYMMDD (es: 20/03/2026 → 20260320)

REGOLE SPECIFICHE PER P.IVA:
- La partita IVA DEVE SEMPRE avere il prefisso "IT" nel JSON di output
- Se il documento mostra "P.IVA 01638060473" senza prefisso, scrivi "IT01638060473"
- Se il documento mostra "P.IVA IT02122760479" con prefisso, scrivi "IT02122760479"
- Le P.IVA italiane hanno SEMPRE 11 cifre dopo il prefisso IT

REGOLE PER PROVINCIA:
- Estrai SEMPRE la sigla provincia (2 lettere) dall'indirizzo se visibile
- Se vedi "51100 PISTOIA PT" → provincia = "PT"
- Se vedi "51039 QUARRATA PT" → provincia = "PT"
- Se vedi "51015 Monsummano Terme" senza sigla, deducila dal CAP: 51xxx = PT (Pistoia)
- Se vedi "51030 Santonuovo" senza sigla, deducila dal CAP: 51xxx = PT (Pistoia)

REGOLE PER RIFERIMENTO ORDINE:
- Cerca riferimenti a ordini sia nella testata che nelle righe articolo
- Se le descrizioni delle righe contengono "OC 2/2003" o simili, quello è il riferimento ordine
- Estrailo nel campo riferimento_ordine della testata
- Formato comune: "OC" + numero/anno oppure "Ordine cliente n. XXX del DD/MM/YYYY"

REGOLE PER DOCUMENTI MANOSCRITTI:
- Per i DDT scritti a mano, fai del tuo meglio per decifrare la calligrafia
- ATTENZIONE alle quantità: se leggi "01" scritto a mano, è quasi certamente 1 (uno), non 0.1
- Nei DDT le quantità sono tipicamente numeri interi (1, 2, 3, 10, etc.) specialmente per pezzi/mobili
- Se la quantità sembra un decimale strano (0.1, 0.2) su un DDT di mobili/arredamento, probabilmente è un intero letto male

Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza markdown, senza commenti, senza testo aggiuntivo.
"""

USER_PROMPT = """\
Analizza questa immagine di un DDT (Documento di Trasporto) fornitore ed estrai i dati nel seguente formato JSON:

{
  "testata": {
    "tipo_documento": "DDT",
    "numero_documento": "<numero del DDT>",
    "data_documento": "<data in formato YYYYMMDD>",
    "fornitore": {
      "ragione_sociale": "<nome fornitore/cedente>",
      "indirizzo": "<indirizzo completo>",
      "cap": "<CAP>",
      "citta": "<città>",
      "provincia": "<sigla provincia 2 lettere — OBBLIGATORIA, deducila dal CAP se non esplicita>",
      "partita_iva": "<P.IVA SEMPRE con prefisso IT, es: IT01638060473>",
      "codice_fiscale": "<CF se presente>"
    },
    "destinatario": {
      "ragione_sociale": "<nome destinatario/cessionario>",
      "indirizzo": "<indirizzo>",
      "cap": "<CAP>",
      "citta": "<città>",
      "provincia": "<sigla provincia 2 lettere>",
      "partita_iva": "<P.IVA SEMPRE con prefisso IT>"
    },
    "causale_trasporto": "<causale es. VENDITA>",
    "aspetto_beni": "<aspetto esteriore>",
    "trasporto_a_mezzo": "<mittente/destinatario/vettore>",
    "pagamento": "<condizioni pagamento se presenti>",
    "riferimento_ordine": "<riferimento a ordine — cerca sia in testata che nelle descrizioni righe, es: OC 2/2003>",
    "codice_conto_mexal": "<codice conto Mexal se visibile, es. 501.00152>",
    "numero_colli": null,
    "peso_kg": null,
    "note": "<eventuali annotazioni>"
  },
  "righe": [
    {
      "riga_num": 1,
      "codice_articolo": "<codice articolo se presente>",
      "descrizione": "<descrizione articolo SENZA il riferimento ordine, es: 'BRACCIOLI BOBOLI' non 'BRACCIOLI BOBOLI OC 2/2003'>",
      "unita_misura": "<UM: Mt, Pz, Kg, Nr, ecc. — se non esplicita, deduci: per mobili/arredamento usa Pz>",
      "quantita": 0.0,
      "prezzo_unitario": null,
      "importo": null,
      "sconto": null,
      "aliquota_iva": "<codice IVA es. 22>"
    }
  ],
  "metadati_ocr": {
    "qualita_lettura": "<alta/media/bassa>",
    "tipo_documento_originale": "<digitale/scansione/manoscritto>",
    "campi_incerti": ["<lista campi dove la lettura è incerta>"]
  }
}
"""


def pdf_to_base64_image(pdf_path: str, page: int = 1, dpi: int = IMAGE_DPI) -> str:
    """
    Converte una pagina PDF in immagine JPEG e restituisce il base64.
    Usa pdftoppm (poppler-utils) per la rasterizzazione.
    Se pdftoppm non è disponibile, prova con pdf2image/Pillow.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        prefix = os.path.join(tmpdir, "page")

        try:
            # Metodo 1: pdftoppm (più veloce, sempre disponibile su Linux)
            result = subprocess.run(
                [
                    "pdftoppm", "-jpeg", "-r", str(dpi),
                    "-f", str(page), "-l", str(page),
                    pdf_path, prefix,
                ],
                capture_output=True, timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"pdftoppm error: {result.stderr.decode()}")

            # pdftoppm genera nomi tipo page-1.jpg o page-01.jpg
            jpg_files = sorted(Path(tmpdir).glob("page-*.jpg"))
            if not jpg_files:
                raise FileNotFoundError("pdftoppm non ha generato immagini")

            img_path = jpg_files[0]

        except (FileNotFoundError, RuntimeError):
            # Metodo 2: fallback con pdf2image
            logger.info("pdftoppm non disponibile, uso pdf2image come fallback")
            from pdf2image import convert_from_path

            images = convert_from_path(
                pdf_path, dpi=dpi, first_page=page, last_page=page,
                fmt="jpeg",
            )
            img_path = os.path.join(tmpdir, "page.jpg")
            images[0].save(img_path, "JPEG", quality=90)

        with open(img_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")


def parse_ddt_with_claude(image_base64: str, filename: str) -> dict:
    """
    Invia l'immagine del DDT a Claude API per OCR + parsing strutturato.
    Restituisce il dizionario con i dati estratti.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Variabile d'ambiente ANTHROPIC_API_KEY non impostata.\n"
            "Esegui: export ANTHROPIC_API_KEY='sk-ant-...'"
        )

    client = anthropic.Anthropic(api_key=api_key)

    logger.info("Invio immagine a Claude API per analisi OCR...")

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": USER_PROMPT,
                    },
                ],
            }
        ],
    )

    # Estrai il testo dalla risposta
    raw_text = response.content[0].text.strip()

    # Pulisci eventuali markdown code fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]  # rimuovi prima riga ```json
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0]
    raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("Claude ha restituito JSON non valido: %s", e)
        logger.error("Risposta grezza:\n%s", raw_text[:500])
        # Salva la risposta grezza per debug
        parsed = {
            "errore": "JSON non valido nella risposta Claude",
            "risposta_grezza": raw_text[:2000],
        }

    # Post-processing: fix P.IVA senza prefisso IT
    _fix_piva(parsed)

    # Aggiungi metadati di processing
    parsed["_processing"] = {
        "file_origine": filename,
        "modello_ai": CLAUDE_MODEL,
        "timestamp": datetime.now().isoformat(),
        "tokens_input": response.usage.input_tokens,
        "tokens_output": response.usage.output_tokens,
    }

    return parsed


def _fix_piva(data: dict):
    """Post-processing: assicura che tutte le P.IVA abbiano prefisso IT."""
    for section in ["fornitore", "destinatario"]:
        testata = data.get("testata", {})
        soggetto = testata.get(section, {})
        if not soggetto:
            continue
        piva = soggetto.get("partita_iva")
        if piva and not piva.startswith("IT"):
            # Verifica che sia una P.IVA italiana (11 cifre)
            digits = piva.replace(" ", "")
            if len(digits) == 11 and digits.isdigit():
                soggetto["partita_iva"] = f"IT{digits}"
                logger.info("Fix P.IVA %s: aggiunto prefisso IT → IT%s", section, digits)


def process_single_pdf(pdf_path: str, output_dir: Optional[str] = None) -> dict:
    """
    Pipeline completa per un singolo PDF:
    1. Rasterizza PDF → immagine
    2. Invia a Claude → JSON strutturato
    3. Salva JSON output
    """
    pdf_path = os.path.abspath(pdf_path)
    filename = os.path.basename(pdf_path)

    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)

    logger.info("=" * 60)
    logger.info("Processing: %s", filename)
    logger.info("=" * 60)

    # Step 1: PDF → immagine base64
    logger.info("Step 1: Rasterizzazione PDF a %d DPI...", IMAGE_DPI)
    image_b64 = pdf_to_base64_image(pdf_path)
    logger.info("  Immagine generata (%d KB base64)", len(image_b64) // 1024)

    # Step 2: Immagine → Claude → JSON
    logger.info("Step 2: Analisi OCR con Claude API...")
    result = parse_ddt_with_claude(image_b64, filename)

    # Step 3: Salva output JSON
    json_filename = Path(filename).stem + "_parsed.json"
    json_path = os.path.join(output_dir, json_filename)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("Step 3: Output salvato in %s", json_path)

    # Riepilogo
    if "testata" in result:
        t = result["testata"]
        logger.info("  Fornitore: %s", t.get("fornitore", {}).get("ragione_sociale", "?"))
        logger.info("  P.IVA: %s", t.get("fornitore", {}).get("partita_iva", "?"))
        logger.info("  DDT n. %s del %s", t.get("numero_documento", "?"), t.get("data_documento", "?"))
        logger.info("  Righe estratte: %d", len(result.get("righe", [])))
        logger.info("  Rif. ordine: %s", t.get("riferimento_ordine", "-"))
        meta = result.get("metadati_ocr", {})
        logger.info("  Qualità lettura: %s", meta.get("qualita_lettura", "?"))
        logger.info("  Tipo originale: %s", meta.get("tipo_documento_originale", "?"))
        if meta.get("campi_incerti"):
            logger.warning("  Campi incerti: %s", ", ".join(meta["campi_incerti"]))

    return result


def main():
    """Entry point — accetta un file PDF o una cartella."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("Uso: python ddt_parser.py <file.pdf | cartella/>")
        sys.exit(1)

    target = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if os.path.isdir(target):
        pdf_files = sorted(Path(target).glob("*.pdf"))
        if not pdf_files:
            logger.error("Nessun file PDF trovato in %s", target)
            sys.exit(1)
        logger.info("Trovati %d file PDF da processare", len(pdf_files))
        results = []
        for pdf_file in pdf_files:
            try:
                result = process_single_pdf(str(pdf_file), output_dir)
                results.append(result)
            except Exception as e:
                logger.error("Errore processing %s: %s", pdf_file.name, e)
                results.append({"errore": str(e), "file": pdf_file.name})
        # Salva anche un riepilogo
        summary_path = os.path.join(output_dir or target, "_riepilogo_batch.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "totale_processati": len(results),
                    "con_errori": sum(1 for r in results if "errore" in r),
                    "timestamp": datetime.now().isoformat(),
                    "risultati": results,
                },
                f, ensure_ascii=False, indent=2,
            )
        logger.info("Riepilogo batch salvato in %s", summary_path)
    elif os.path.isfile(target):
        if not target.lower().endswith(".pdf"):
            logger.error("Il file deve essere un PDF: %s", target)
            sys.exit(1)
        process_single_pdf(target, output_dir)
    else:
        logger.error("Percorso non trovato: %s", target)
        sys.exit(1)


if __name__ == "__main__":
    main()