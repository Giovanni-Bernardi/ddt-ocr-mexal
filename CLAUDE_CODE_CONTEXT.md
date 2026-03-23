# DDT Fornitore → Mexal — Contesto Progetto

## Obiettivo
Web app Streamlit per importare DDT fornitore (PDF scansionati/manoscritti) in Mexal/Passepartout tramite OCR + WebAPI REST.

## Flusso
1. Upload PDF DDT fornitore
2. OCR con Claude API (immagine → JSON strutturato)
3. Preview e correzione dati (fornitore, articoli, quantità)
4. Lookup fornitore/articoli in Mexal via WebAPI
5. Creazione BF (Bolla Fornitore) in Mexal via POST

## File del progetto
```
ddt_ocr_mexal/
├── app.py                  ← Web app Streamlit (QUESTO FILE è il focus)
├── ddt_parser.py           ← Script OCR standalone (v1.1)
├── ddt_to_mexal.py         ← Converter JSON → payload Mexal
├── mexal_client.py         ← Client API Mexal con doppio token auth
├── ddt_samples/            ← PDF di test + JSON generati
│   ├── DOC_1_Carradori.pdf
│   ├── DOC_2_Girasoli.pdf
│   ├── DOC_3_OPE.pdf
│   └── *_parsed.json
└── CLAUDE_CODE_CONTEXT.md  ← Questo file
```

## Architettura Autenticazione Mexal
L'API Mexal richiede **due token base64** nell'header Authorization:
```
Authorization: Passepartout <base64(WEBAPI_USER:WEBAPI_PWD)> <base64(ADMIN_USER:ADMIN_PWD)> DOMINIO=mantellassi
```
Header aggiuntivi obbligatori:
```
Content-Type: application/json
Coordinate-Gestionale: Azienda=SUT Anno=2026
```

## Endpoint API Mexal utilizzati

### Fornitori
- `GET /risorse/fornitori?max=N` — Lista fornitori
- `GET /risorse/fornitori/{codice}` — Singolo fornitore (es: 601.00072)
- `POST /risorse/fornitori/ricerca` — Ricerca con filtri

### Articoli
- `GET /risorse/articoli?max=N` — Lista articoli
- `GET /risorse/articoli/{codice}` — Singolo articolo
- `POST /risorse/articoli/ricerca` — Ricerca

### Creazione BF (Bolla Fornitore)
```
POST /risorse/documenti/movimenti-magazzino
```
Payload esempio (TESTATO E FUNZIONANTE — 201 Created):
```json
{
  "sigla": "BF",
  "serie": 1,
  "numero": 2,
  "data_documento": "20260323",
  "cod_conto": "601.00022",
  "id_magazzino": 1,
  "id_riga": [[1, 1]],
  "tp_riga": [[1, "R"]],
  "codice_articolo": [[1, "26MST/K8/0000"]],
  "quantita": [[1, 10]],
  "cod_iva": [[1, "22"]],
  "sigla_ordine": [],
  "serie_ordine": [],
  "numero_ordine": [],
  "sigla_doc_orig": [],
  "serie_doc_orig": [],
  "numero_doc_orig": [],
  "id_rif_testata": []
}
```

**IMPORTANTE:**
- Il campo `numero` per le BF è OBBLIGATORIO (non può essere 0/auto)
- NON usare il campo `descrizione_riga` — non esiste, causa errore 400
- I codici fornitore hanno formato `601.xxxxx` (mastro 601)
- I codici cliente hanno formato `501.xxxxx` (mastro 501)
- Gli array di riga hanno formato `[[indice, valore], ...]`
- Il campo `cod_iva` vuole una stringa: `"22"` non `22`

## Formato filtri ricerca Mexal
```json
{
  "filtri": [
    {
      "campo": "partita_iva",
      "condizione": "=",
      "valore": "01449570470"
    }
  ]
}
```
Condizioni disponibili: `=`, `>`, `<`, `>=`, `<=`, `contiene`, `inizia`, `finisce`
Opzione: `"case_insensitive": true`

## OCR — Prompt Claude
Il prompt di sistema istruisce Claude a:
- Estrarre dati da immagini DDT (digitali, scansioni, manoscritti)
- Restituire JSON strutturato con testata + righe
- P.IVA sempre con prefisso IT
- Date in formato YYYYMMDD
- Quantità come numeri decimali (punto, non virgola)
- Provincia dedotta dal CAP se non esplicita
- Riferimento ordine cercato anche nelle descrizioni righe

Modello: `claude-sonnet-4-20250514`
Costo: ~$0.01-0.02 per DDT

## Formato JSON output OCR
```json
{
  "testata": {
    "tipo_documento": "DDT",
    "numero_documento": "2096",
    "data_documento": "20260320",
    "fornitore": {
      "ragione_sociale": "CARRADORI & CO. S.R.L.",
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
      "partita_iva": "IT02078250475"
    },
    "causale_trasporto": "VENDITE",
    "aspetto_beni": "A vista",
    "trasporto_a_mezzo": "MITTENTE",
    "pagamento": "RIMESSA DIRETTA",
    "riferimento_ordine": "Ordine cliente n. 490 del 04/03/2026",
    "codice_conto_mexal": "601.00072",
    "note": null
  },
  "righe": [
    {
      "riga_num": 1,
      "codice_articolo": "TTEFLSEX",
      "descrizione": "TESSUTO PL/CO/AF ART.FSL-SOFABLE COL.110",
      "unita_misura": "Mt",
      "quantita": 411.6,
      "prezzo_unitario": null,
      "aliquota_iva": "22"
    }
  ],
  "metadati_ocr": {
    "qualita_lettura": "alta",
    "tipo_documento_originale": "digitale",
    "campi_incerti": []
  }
}
```

## Azienda cliente
- **Azienda**: Sutor Lab Home S.R.L. (Azienda Mexal: SUT)
- **Settore**: Produzione mobili imbottiti (divani, poltrone)
- **Fornitori tipici**: tessuti, imbottiture, strutture legno, ferramenta
- **DDT tipici**: tessuti a metraggio (Mt), componenti a pezzi (Pz/NR), materiali a peso (KG)

## Personalizzazioni richieste per la UI
L'utente vuole migliorare l'interfaccia Streamlit. Alcune idee:
- Tema/colori coerenti con il brand
- Gestione errori API più robusta (retry su 529 overloaded)
- Batch upload (più DDT alla volta)
- Salvataggio credenziali in .env o config locale
- Storico persistente delle BF create
- Preview immagine del DDT accanto ai dati estratti

## Note tecniche
- Python 3.9 (Mac)
- pdftoppm (poppler) per rasterizzare i PDF
- Il warning urllib3/LibreSSL è innocuo, ignoralo
- Per lanciare Streamlit: `python3 -m streamlit run app.py`
