"""OCR engine — converte PDF DDT in JSON strutturato via Claude API."""

import base64
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic

from lib.ui_common import get_secret

MAX_RETRIES = 3
RETRY_BASE_DELAY = 3

SYSTEM_PROMPT = """\
Sei un esperto contabile italiano specializzato nella lettura di Documenti di Trasporto (DDT).
Il tuo compito è estrarre tutti i dati strutturati da un'immagine di DDT fornitore.

REGOLE IMPORTANTI:
- Estrai ESATTAMENTE ciò che vedi, non inventare dati mancanti
- Per i campi non presenti o illeggibili, usa null
- Le quantità devono essere numeri (usa il punto come separatore decimale: 411,6 → 411.6)
- Le date devono essere in formato YYYYMMDD (es: 20/03/2026 → 20260320)
- La P.IVA DEVE SEMPRE avere il prefisso "IT"
- Estrai SEMPRE la sigla provincia (2 lettere), deducila dal CAP se non esplicita (51xxx = PT)
- Cerca riferimenti a ordini sia in testata che nelle descrizioni righe
- Per DDT manoscritti: "01" è quasi certamente 1, non 0.1

Rispondi ESCLUSIVAMENTE con un oggetto JSON valido.
"""

USER_PROMPT = """\
Analizza questa immagine di DDT fornitore ed estrai i dati in questo formato JSON:

{
  "testata": {
    "tipo_documento": "DDT",
    "numero_documento": "<numero>",
    "data_documento": "<YYYYMMDD>",
    "fornitore": {
      "ragione_sociale": "<nome>",
      "indirizzo": "<indirizzo>",
      "cap": "<CAP>",
      "citta": "<città>",
      "provincia": "<2 lettere>",
      "partita_iva": "<con prefisso IT>",
      "codice_fiscale": "<CF>"
    },
    "destinatario": {
      "ragione_sociale": "<nome>",
      "indirizzo": "<indirizzo>",
      "cap": "<CAP>",
      "citta": "<città>",
      "provincia": "<2 lettere>",
      "partita_iva": "<con prefisso IT>"
    },
    "causale_trasporto": "<causale>",
    "aspetto_beni": "<aspetto>",
    "trasporto_a_mezzo": "<mittente/destinatario/vettore>",
    "pagamento": "<condizioni>",
    "riferimento_ordine": "<riferimento ordine>",
    "codice_conto_mexal": "<codice conto se visibile>",
    "note": null
  },
  "righe": [
    {
      "riga_num": 1,
      "codice_articolo": "<codice>",
      "descrizione": "<descrizione SENZA riferimento ordine>",
      "unita_misura": "<UM>",
      "quantita": 0.0,
      "prezzo_unitario": null,
      "aliquota_iva": "<codice IVA>"
    }
  ],
  "metadati_ocr": {
    "qualita_lettura": "<alta/media/bassa>",
    "tipo_documento_originale": "<digitale/scansione/manoscritto>",
    "campi_incerti": []
  }
}
"""


def pdf_to_base64(pdf_bytes: bytes, dpi: int = 200) -> str:
    """Converte PDF bytes in immagine JPEG base64."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        prefix = os.path.join(tmpdir, "page")
        result = subprocess.run(
            ["pdftoppm", "-jpeg", "-r", str(dpi), "-f", "1", "-l", "1", pdf_path, prefix],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftoppm error: {result.stderr.decode()}")
        jpg_files = sorted(Path(tmpdir).glob("page-*.jpg"))
        if not jpg_files:
            raise FileNotFoundError("Nessuna immagine generata")
        with open(jpg_files[0], "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")


def ocr_ddt(pdf_bytes: bytes, api_key: str, status_callback=None) -> tuple[dict, str]:
    """PDF → immagine → Claude → JSON.  Returns (parsed_data, image_b64)."""
    if status_callback:
        status_callback("Conversione PDF in immagine...")
    image_b64 = pdf_to_base64(pdf_bytes)

    client = anthropic.Anthropic(api_key=api_key)
    response = None
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if status_callback:
                msg = f"Tentativo {attempt}/{MAX_RETRIES} — OCR in corso..." if attempt > 1 else "OCR in corso con Claude..."
                status_callback(msg)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                        {"type": "text", "text": USER_PROMPT},
                    ],
                }],
            )
            break
        except anthropic.APIStatusError as e:
            last_error = e
            if e.status_code in (529, 500, 502, 503) and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * attempt
                if status_callback:
                    status_callback(f"Errore {e.status_code} — retry tra {delay}s (tentativo {attempt}/{MAX_RETRIES})...")
                time.sleep(delay)
                continue
            raise
        except anthropic.APIConnectionError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * attempt
                if status_callback:
                    status_callback(f"Errore connessione — retry tra {delay}s...")
                time.sleep(delay)
                continue
            raise

    if response is None:
        raise last_error or RuntimeError("OCR fallito dopo tutti i tentativi")

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    parsed = json.loads(raw.strip())

    for section in ["fornitore", "destinatario"]:
        sogg = parsed.get("testata", {}).get(section, {})
        if sogg:
            piva = sogg.get("partita_iva")
            if piva and not piva.startswith("IT"):
                digits = piva.replace(" ", "")
                if len(digits) == 11 and digits.isdigit():
                    sogg["partita_iva"] = f"IT{digits}"

    parsed["_processing"] = {
        "timestamp": datetime.now().isoformat(),
        "tokens_input": response.usage.input_tokens,
        "tokens_output": response.usage.output_tokens,
    }
    return parsed, image_b64
