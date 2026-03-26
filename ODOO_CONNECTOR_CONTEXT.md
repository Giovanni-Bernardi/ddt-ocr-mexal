# Connettore Odoo CRM → Webapp → Mexal

## Obiettivo
Quando un lead CRM in Odoo passa allo stage "Won", i dati del prospect vengono mostrati nella webapp in una coda di validazione. L'operatore verifica/corregge i dati e conferma la creazione del cliente in Mexal.

## Architettura
```
Odoo CRM (stage → "Won") 
    → Webapp polling/webhook (legge lead "Won" non ancora processati)
        → Coda validazione (operatore verifica dati)
            → Creazione cliente in Mexal SOF (POST /clienti)
                → Codice cliente 501.xxxxx pronto per l'OC
```

## Connessione Odoo

### Server
- URL: https://odoo.mantellassi.com
- Database: odoo.mantellassi.com
- Versione: Odoo 16 Enterprise
- Aziende: Sofable srl (id: 2), Mantellassi (id: 1)

### Autenticazione (JSON-RPC)
```
POST https://odoo.mantellassi.com/web/session/authenticate
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "params": {
    "db": "odoo.mantellassi.com",
    "login": "ODOO_USERNAME",
    "password": "ODOO_PASSWORD"
  }
}
```
Risposta: uid nel result + cookie di sessione da riusare nelle chiamate successive.

Le credenziali vanno nei Secrets di Streamlit:
```toml
ODOO_URL = "https://odoo.mantellassi.com"
ODOO_DB = "odoo.mantellassi.com"
ODOO_USERNAME = "..."
ODOO_PASSWORD = "..."
```

### Chiamate API (JSON-RPC via /web/dataset/call_kw)
Tutte le chiamate usano:
```
POST https://odoo.mantellassi.com/web/dataset/call_kw
Content-Type: application/json
Cookie: <session cookie dall'autenticazione>
```

### Leggere lead CRM
```json
{
  "jsonrpc": "2.0",
  "params": {
    "model": "crm.lead",
    "method": "search_read",
    "args": [[["stage_id", "=", 4], ["type", "=", "opportunity"]]],
    "kwargs": {
      "fields": ["name", "partner_name", "contact_name", "email_from", "phone", "street", "city", "zip", "state_id", "country_id", "partner_id", "stage_id", "date_closed", "user_id"],
      "limit": 50,
      "order": "date_closed desc"
    }
  }
}
```

### Leggere dettagli partner (per CF e P.IVA)
Se il lead ha un partner_id collegato:
```json
{
  "jsonrpc": "2.0",
  "params": {
    "model": "res.partner",
    "method": "read",
    "args": [[PARTNER_ID]],
    "kwargs": {
      "fields": ["name", "email", "phone", "street", "city", "zip", "state_id", "country_id", "vat", "l10n_it_codice_fiscale", "company_type"]
    }
  }
}
```

### Campi importanti
| Campo Odoo | Tipo | Mapping Mexal |
|---|---|---|
| partner_name | string | ragione_sociale |
| email_from | string | email |
| phone | string | telefono |
| street | string | indirizzo |
| city | string | localita |
| zip | string | cap |
| state_id | [id, "nome"] | provincia (estrarre sigla) |
| country_id | [id, "nome"] | cod_paese |
| vat | string | partita_iva (senza prefisso IT per Mexal) |
| l10n_it_codice_fiscale | string | codice_fiscale |
| company_type | "person"/"company" | gest_per_fisica (S/N) |

### Stage CRM pipeline
| ID | Nome | is_won | Sequence |
|---|---|---|---|
| 1 | New | false | 0 |
| 7 | Proposta in preparazione | false | 1 |
| 2 | Qualified | false | 2 |
| 3 | Proposition | false | 3 |
| 8 | Trattativa tiepida | false | 4 |
| 4 | **Won** | **true** | 5 |
| 6 | Stand By | false | 6 |
| 5 | Persa | false | 7 |

**TRIGGER**: stage_id = 4 (Won, is_won = true)

## Interfaccia nella Webapp

### Nuova pagina: "Coda Clienti da Odoo" (pages/4_🔄_Coda_Odoo.py)

#### Sezione 1: Sincronizzazione
- Bottone "Aggiorna da Odoo" che chiama l'API e legge tutti i lead con stage "Won"
- Mostra quanti nuovi lead sono stati trovati
- In futuro: polling automatico ogni 5 minuti

#### Sezione 2: Lista lead da processare
- Tabella con: Nome, Email, Telefono, Città, Data Won
- Stato: "Da validare" / "Creato in Mexal" / "Errore"
- Click su una riga per espandere i dettagli

#### Sezione 3: Form validazione (per ogni lead)
- Dati precompilati da Odoo
- Campi editabili: ragione_sociale, cognome, nome, codice_fiscale, indirizzo, cap, città, provincia, P.IVA, telefono, email
- Toggle persona fisica / società
- Evidenzia campi mancanti obbligatori per Mexal (codice_fiscale!)
- Bottone "Crea cliente in Mexal"
- Dopo creazione: mostra codice assegnato (501.xxxxx)

#### Sezione 4: Storico
- Lista clienti già creati con codice Mexal

## Creazione cliente Mexal (reminder)
```
POST https://services.passepartout.cloud/webapi/risorse/clienti
Header: Azienda=SOF Anno=2026

{
  "codice": "501.AUTO",
  "ragione_sociale": "NOME CLIENTE",
  "tp_nazionalita": "I",
  "cod_paese": "IT",
  "codice_fiscale": "OBBLIGATORIO",
  "cod_listino": 1,
  "valuta": 1,
  "gest_per_fisica": "S",
  "cognome": "COGNOME",
  "nome": "NOME",
  "indirizzo": "VIA...",
  "cap": "50129",
  "localita": "FIRENZE",
  "provincia": "FI"
}
```

## Note tecniche
- Odoo usa JSON-RPC, non REST. Le chiamate sono tutte POST su /web/dataset/call_kw
- L'autenticazione crea una sessione con cookie. Salvare il cookie e riusarlo.
- Il campo state_id di Odoo restituisce [id, "Firenze (IT)"] — estrarre la sigla provincia con regex o mapping
- Il campo vat di Odoo include a volte il prefisso IT, a volte no — normalizzare
- Per la provincia: state_id contiene "Firenze (IT)" → provincia = "FI". Usare la parte tra parentesi o mappare.
- company_type "person" → gest_per_fisica="S", "company" → gest_per_fisica="N"
