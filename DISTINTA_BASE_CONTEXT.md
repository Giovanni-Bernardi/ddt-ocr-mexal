# Fase C — Distinta Base e Produzione

## Obiettivo
Aggiungere alla webapp una pagina per gestire lo sviluppo della distinta base:
1. Simulare l'esplosione componenti di un articolo prodotto finito
2. Creare la BL (Bolla di Lavorazione) collegata a un OC esistente
3. Visualizzare componenti e fasi di lavorazione

## API Mexal — Sviluppo Distinta Base

### Endpoint
```
POST https://services.passepartout.cloud/webapi/servizi
```
Header: `Azienda=SUT Anno=2026`

### Payload
```json
{
  "cmd": "sviluppo_distinta_base",
  "dati": {
    "codice_articolo": "BOB145FSDSA27KMIMB",
    "codice_art_padre": "",
    "codice_cliente": "",
    "data_documento": "20260327",
    "codice": 0,
    "cod_sottobolla": 0,
    "nr_rif_pf": 0,
    "id_riga_oc": 0,
    "quantita_taglie": [[1, 1]]
  }
}
```

### Parametri importanti
- `codice_articolo`: codice del prodotto finito (deve avere gest_dbp="S")
- `id_riga_oc`: 0 = SIMULAZIONE (restituisce componenti senza creare BL). Con id_riga reale = CREA BL collegata all'OC
- `quantita_taglie`: per articoli non a taglie, specificare quantità come primo elemento [[1, quantità]]
- `codice_cliente`: opzionale, codice conto cliente
- `data_documento`: data in formato YYYYMMDD

### Risposta (TESTATA E FUNZIONANTE)
La risposta contiene un array `componenti_sviluppati` con tutti i componenti della distinta:

```json
{
  "componenti_sviluppati": [
    {
      "fase": 1.0,
      "codice_componente": "RIVSANTOS27",
      "descrizione_um": "MT",
      "quantita_totale": 6.0,
      "tp_articolo": "A",
      "descrizione_fase": "TAGLIO",
      "numero_codice_fase": 2.0,
      "nota": [[1, "CUCITURA INTERNA"]],
      "magazzino": 1.0
    }
  ]
}
```

### Campi della risposta
| Campo | Descrizione |
|---|---|
| fase | Numero progressivo della fase nella distinta |
| codice_componente | Codice articolo del componente |
| descrizione_um | Unità di misura (MT, MQ, NR, MN) |
| quantita_variabile | Quantità per unità di prodotto finito |
| quantita_totale | Quantità totale (variabile × qty prodotto) |
| tp_articolo | Tipo: A=articolo, L=lavorazione, S=spesa |
| descrizione_fase | Nome della fase (TAGLIO, CUCITO, IMBOTTITURA...) |
| numero_codice_fase | ID della fase in tabella fasi lavorazione |
| nota | Note aggiuntive (array di [indice, testo]) |

### Tipi articolo componente
- `A` = Articolo/materiale da acquistare → genera potenziale OF
- `L` = Lavorazione (tempo/manodopera) → minuti di lavoro
- `S` = Spesa → costi aggiuntivi (minuterie, ecc.)

## Esempio reale: BOBOLI POLTRONA FREESIDE DX MAXI (BOB145FSDSA27KMIMB)

### Fase 1 — TAGLIO (cod_fase: 2)
| Componente | Descrizione | Qty | UM | Tipo | Note |
|---|---|---|---|---|---|
| RIVSANTOS27 | Rivestimento Santos 27 | 6.0 | MT | A | CUCITURA INTERNA |
| RIVPEKELLYMIRROR | Rivestimento pelle Kelly Mirror | 3.0 | MQ | A | BASE |
| FODSOFABLE | Fodera Sofable | 1.5 | MT | A | SEDUTE-SPALLIERE-RETROSPALLIERE-BRACCIOLI |
| FODSOFABLE | Fodera Sofable | 3.0 | MT | A | FODERA BASE |
| LAVTAG | Lavorazione taglio | 90 | MN | L | |

### Fase 2 — CUCITO (cod_fase: 3)
| Componente | Descrizione | Qty | UM | Tipo |
|---|---|---|---|---|
| LAVCUC | Lavorazione cucitura | 120 | MN | L |

### Fase 3 — IMBOTTITURA (cod_fase: 4)
| Componente | Descrizione | Qty | UM | Tipo |
|---|---|---|---|---|
| GOMBOBBRA | Gomma bracciolo | 1 | NR | A |
| GOMBOBELEFSDMAX | Gomma elemento freeside max | 1 | NR | A |
| TRABOBBRA | Telaio bracciolo | 1 | NR | A |
| TRABOBSPAMAX | Telaio spalliera max | 1 | NR | A |
| TRABOBRETSPAMAX | Telaio retro spalliera max | 1 | NR | A |
| TRABOBSEDFSDMAX | Telaio seduta freeside max | 1 | NR | A |
| LAVIMB | Lavorazione imbottitura | 180 | MN | L |
| MINUTERIE | Minuterie | 1 | NR | S |

## Fasi di lavorazione disponibili in Mexal SUT

| ID | Descrizione |
|---|---|
| 1 | FUSTO |
| 2 | TAGLIO |
| 3 | CUCITO |
| 4 | IMBOTTITURA |
| 5 | IMBALLAGGIO |
| 6 | VERNICIATURA |
| 7 | CUCITURA |
| 8 | VERNICIATURA ZAMPE |
| 9 | VERNICIATURA ZAMPE ANTERIORI |
| 10 | VERNICIATURA ZAMPE POSTERIORI |

Endpoint fasi: GET /risorse/dati-generali/fasi-lavorazione

## Articoli BOBOLI in Mexal SUT
- 1.244 articoli BOBOLI totali
- 848 con distinta base (gest_dbp="S") → sviluppabili
- 396 senza distinta base
- Tutti di tipologia "A" (articolo) e cod_natura "PF" (Prodotto Finito)
- Codici iniziano con "BOB" seguito da dimensioni e configurazione

## API Avanzamento Produzione (per riferimento futuro)

```json
{
  "cmd": "avanzamento_produzione",
  "dati": {
    "data_documento": "20260327",
    "codice": 1,
    "cod_sottobolla": 1,
    "nr_rif_pf": 1,
    "tp_operazione": "C",
    "nr_fase": 1,
    "qta_agg_carico": 1
  }
}
```
tp_operazione: "S" = Scarico componenti, "C" = Carico prodotto finito

## Interfaccia nella Webapp

### Nuova pagina: pages/5_🔧_Distinta_Base.py

#### Sezione 1: Ricerca articolo prodotto finito
- Campo di ricerca per codice o descrizione articolo
- POST /risorse/articoli/ricerca con filtro su codice o descrizione
- Filtrare solo articoli con gest_dbp="S" (hanno distinta base)
- Mostra risultati in selectbox: "CODICE — DESCRIZIONE"

#### Sezione 2: Simulazione sviluppo
- Dopo aver selezionato un articolo, campo quantità (default 1)
- Bottone "Simula sviluppo distinta"
- Chiama POST /servizi con cmd=sviluppo_distinta_base e id_riga_oc=0
- Mostra i componenti raggruppati per fase in expander/accordion:
  - Fase 1 — TAGLIO: lista componenti con codice, qty, UM, note
  - Fase 2 — CUCITO: ...
  - Fase 3 — IMBOTTITURA: ...
- Colora diversamente per tipo: verde=materiale (A), blu=lavorazione (L), grigio=spesa (S)
- Mostra totale minuti lavorazione per fase

#### Sezione 3: Collegamento a OC (futuro)
- Seleziona un OC esistente da cui sviluppare
- Mostra le righe dell'OC con articoli che hanno distinta base
- Bottone "Sviluppa distinta per OC" che chiama il servizio con id_riga_oc reale
- Questo crea la BL in Mexal

## Note tecniche
- Il servizio sviluppo_distinta_base è sotto /servizi, non /risorse
- Con id_riga_oc=0 è una simulazione, non crea nulla in Mexal
- La quantità va in quantita_taglie come [[1, qty]] per articoli non a taglie
- Header Azienda=SUT Anno=2026 per tutte le chiamate
- Gli impegni esistenti sono leggibili da GET /risorse/impegni
