# Fase A — Preventivo PDF → OC Mexal + Anagrafica Cliente

## Obiettivo
Estendere la webapp Streamlit con:
1. **Pagina Preventivo → OC**: carica un preventivo Sofable PDF, estrai dati, crea OC in Mexal
2. **Pagina Anagrafica Cliente**: cerca/crea clienti in Mexal (da dati manuali o da Odoo in futuro)

## Architettura multi-page Streamlit
Ristrutturare il progetto in multi-page app:

```
ddt_ocr_mexal/
├── app.py                      ← Home / DDT → BF (esistente, rinominare se serve)
├── pages/
│   ├── 1_📦_DDT_Fornitore.py   ← Spostare qui il codice DDT→BF
│   ├── 2_📋_Preventivo_OC.py   ← NUOVA: Preventivo → OC 
│   ├── 3_👤_Anagrafica.py      ← NUOVA: Gestione clienti
│   └── 4_📜_Storico.py         ← FUTURA: log operazioni
├── lib/
│   ├── __init__.py
│   ├── mexal_api.py            ← Client Mexal condiviso (refactor da mexal_client.py)
│   └── ocr_engine.py           ← OCR Claude condiviso
├── assets/                     ← Loghi, immagini
├── .streamlit/
│   └── config.toml
├── requirements.txt
├── packages.txt
└── CLAUDE_CODE_CONTEXT.md
```

## IMPORTANTE: Struttura preventivo Sofable

I preventivi sono SEMPRE PDF digitali con testo nativo (non scansioni).
Si possono leggere con pdfplumber SENZA bisogno di OCR Claude (più veloce e gratis).
Usare Claude API SOLO come fallback se pdfplumber non riesce a parsare.

### Formato preventivo Sofable (estratto dal PDF reale):

**Testata**:
- "Ordine n° S05375" — numero preventivo/ordine
- "Data offerta: 02/03/2026" — data documento  
- "Scadenza: 26/03/2026"
- Cliente: nome, indirizzo, città, CAP, provincia
- "Addetto vendite: Eva Giusti" — agente
- Emittente: SOFABLE SRL, P.IVA 12502260966

**Righe articolo** (tabella con colonne):
| Descrizione | Misure | Quantità | Prezzo unitario | Sconto % | Imposte | Importo |
|---|---|---|---|---|---|---|
| BOBOLI - Divano (MIDI, 2 posti, Tessuto EXTRA) | L.190 P.105 H.90 | 1,00 Unità | 6.200,00 | 40,00 | 22% | 3.049,18 € |
| BOBOLI Base in pelle (Pelle 700) | | 2,00 Unità | 84,00 | 40,00 | 22% | 82,62 € |
| EXTRA SCONTO | | 1,00 Unità | -392,80 | 0,00 | 22% | -321,97 € |
| CUSCINO PIUMA (45x45, Tessuto EXTRA) | L.45 H.45 | 2,00 Unità | 110,00 | 40,00 | 22% | 108,20 € |

**Totali**:
- Imponibile: 3.032,78 €
- IVA 22%: 667,22 €
- Totale: 3.700,00 €

**Note**: sotto la tabella ci sono note su DX/SX e coordinate bancarie.

### Strategia di parsing:
1. Estrarre testo con pdfplumber
2. Parsare la testata con regex (numero ordine, data, cliente, agente)
3. Parsare le righe dalla tabella (pdfplumber.extract_tables())
4. Se il parsing fallisce, fallback a Claude API con immagine

## API Mexal per creazione OC

### Endpoint
```
POST https://services.passepartout.cloud/webapi/risorse/documenti/ordini-clienti
```

### Nomi campi API OC su SUT — IDENTICI a movimenti magazzino
Su azienda SUT i nomi campi per gli ordini-clienti sono gli stessi dei movimenti-magazzino:

| Campo | Nome API |
|-------|----------|
| Codice cliente | `cod_conto` |
| Data documento | `data_documento` |
| Codice articolo | `codice_articolo` |
| Aliquota IVA | `cod_iva` |
| Quantità | `quantita` |
| Sigla | `sigla` |
| Serie | `serie` |
| Numero | `numero` |

### IMPORTANTE: `numero: 0` funziona per gli OC (numerazione automatica)
A differenza delle BF dove il numero è obbligatorio, per gli OC si può usare `numero: 0` e Mexal assegna automaticamente il prossimo numero disponibile.

### Payload esempio OC (VERIFICATO su SUT):
```json
{
  "sigla": "OC",
  "serie": 1,
  "numero": 0,
  "data_documento": "20260302",
  "cod_conto": "501.00022",
  "id_riga": [[1, 1], [2, 2], [3, 3]],
  "tp_riga": [[1, "R"], [2, "R"], [3, "R"]],
  "codice_articolo": [[1, "ART001"], [2, "ART002"], [3, "ART003"]],
  "quantita": [[1, 1], [2, 2], [3, 1]],
  "prezzo": [[1, 6200.00], [2, 84.00], [3, 120.00]],
  "sconto": [[1, "40"], [2, "40"], [3, "40"]],
  "cod_iva": [[1, "22"], [2, "22"], [3, "22"]]
}
```

### Campi aggiuntivi utili per l'OC:
- `prezzo`: array [[indice, valore]] — prezzo unitario per riga
- `sconto`: array [[indice, "40"]] — percentuale sconto per riga
- `descr_riga`: array [[indice, "testo"]] — descrizione per righe senza codice articolo
- `codice_agente`: stringa — codice agente (es: "601.00001")
- `nota`: array di stringhe — note documento

### Per verificare TUTTI i campi disponibili:
```
GET /risorse/documenti/ordini-clienti?info=true
```
Con header Coordinate-Gestionale: Azienda=SUT Anno=2026

## GESTIONE DOPPIA AZIENDA

CRITICO: le WebAPI usano DUE aziende diverse nell'header Coordinate-Gestionale:
- **SOF** per anagrafiche (clienti, fornitori): `Azienda=SOF Anno=2026`
- **SUT** per documenti (OC, BF) e articoli: `Azienda=SUT Anno=2026`

## API Mexal per anagrafica clienti (Azienda SOF!)

### Creazione cliente — TESTATO 201 OK
```
POST https://services.passepartout.cloud/webapi/risorse/clienti
Header: Coordinate-Gestionale: Azienda=SOF Anno=2026
```

Campi OBBLIGATORI (senza questi → errore 400):
- `codice`: "501.AUTO" (numerazione automatica)
- `ragione_sociale`
- `tp_nazionalita`: "I"
- `cod_paese`: "IT"
- `codice_fiscale` (senza → errore "Partita iva e codice fiscale assenti")
- `cod_listino`: 1 (senza → errore "Il listino deve essere compreso tra 1 e 999")
- `valuta`: 1 (senza → errore "Valuta estera errata")

Campi opzionali:
- `gest_per_fisica`: "S" per persone fisiche, "N" per società
- `cognome`, `nome` (per persone fisiche)
- `indirizzo`, `cap`, `localita`, `provincia`
- `partita_iva`, `telefono`, `email`, `pec`

Payload testato e funzionante:
```json
{
  "codice": "501.AUTO",
  "ragione_sociale": "BERNARDI GIOVANNI",
  "tp_nazionalita": "I",
  "cod_paese": "IT",
  "gest_per_fisica": "S",
  "cognome": "BERNARDI",
  "nome": "GIOVANNI",
  "codice_fiscale": "BRNGNN90A01F205X",
  "indirizzo": "VIA TEST 1",
  "cap": "20129",
  "localita": "MILANO",
  "provincia": "MI",
  "cod_listino": 1,
  "valuta": 1
}
```

### Cancellazione cliente
```
DELETE /risorse/clienti/{codice}
Header: Coordinate-Gestionale: Azienda=SOF Anno=2026
```

### Ricerca cliente
```
POST /risorse/clienti/ricerca
{
  "filtri": [
    {"campo": "ragione_sociale", "condizione": "contiene", "case_insensitive": true, "valore": "GIOVANNI"}
  ]
}
```

### Lettura singolo cliente
```
GET /risorse/clienti/501.00022
```

## Formato JSON output parser preventivo

```json
{
  "testata": {
    "tipo_documento": "PREVENTIVO",
    "numero_preventivo": "S05375",
    "data_offerta": "20260302",
    "data_scadenza": "20260326",
    "cliente": {
      "nome": "Maria Antonietta di Giovanni",
      "indirizzo": "Via Santa Reparata 13",
      "cap": "50129",
      "citta": "Firenze",
      "provincia": "FI"
    },
    "addetto_vendite": "Eva Giusti",
    "emittente": {
      "ragione_sociale": "SOFABLE SRL",
      "partita_iva": "12502260966"
    },
    "totale_imponibile": 3032.78,
    "totale_iva": 667.22,
    "totale_documento": 3700.00
  },
  "righe": [
    {
      "riga_num": 1,
      "descrizione": "BOBOLI - Divano (MIDI, 2 posti, Tessuto EXTRA)",
      "dettaglio_rivestimento": "Tessuto EXTRA: MUMBLE 13 + KELLY APRICOT",
      "misure": "L. 190 cm - P. 105 cm - H. 90 cm",
      "quantita": 1.0,
      "prezzo_unitario": 6200.00,
      "sconto_percentuale": 40.0,
      "aliquota_iva": "22",
      "importo": 3049.18
    }
  ]
}
```

## Interfaccia pagina Preventivo → OC

### Step 1: Upload preventivo PDF
- Drag & drop PDF
- Estrazione automatica con pdfplumber (no OCR)
- Preview PDF accanto ai dati estratti

### Step 2: Verifica dati
- Dati cliente con lookup in Mexal (cerca per nome/CF)
- Se cliente non trovato: bottone "Crea cliente in Mexal"
- Righe articolo con lookup articoli in Mexal
- Prezzo, sconto, importo editabili
- Totali calcolati automaticamente

### Step 3: Crea OC
- Numero OC: automatico (0) o manuale
- Preview payload JSON
- Bottone "Crea OC in Mexal"
- Feedback professionale (no palloncini!)

## Interfaccia pagina Anagrafica Cliente

### Ricerca cliente
- Campo ricerca per nome, CF, P.IVA, codice Mexal
- Risultati in tabella con selezione

### Crea nuovo cliente
- Toggle "Persona fisica / Società"
- Campi obbligatori: ragione_sociale (o cognome+nome), codice_fiscale, cod_listino=1, valuta=1
- Campi opzionali: indirizzo, CAP, città, provincia, P.IVA, telefono, email, PEC
- Codice: 501.AUTO (automatico)
- Bottone "Crea in Mexal" + bottone "Annulla" per eliminare l'ultimo creato
- IMPORTANTE: creazione su Azienda=SOF (non SUT!)
- In futuro: bottone "Importa da Odoo" (placeholder)

## Note tecniche
- Python 3.9 (Mac del developer)
- pdfplumber per estrazione testo PDF (già installato)
- Autenticazione Mexal: doppio token base64 (vedi CLAUDE_CODE_CONTEXT.md)
- Le credenziali sono nei Secrets di Streamlit
- L'app è deployata su Streamlit Cloud: https://ocr-sofable.streamlit.app/
- Repo GitHub: https://github.com/Giovanni-Bernardi/ddt-ocr-mexal
- Azienda Mexal: SUT, Anno: 2026
