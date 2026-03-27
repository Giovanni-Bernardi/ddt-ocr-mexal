# Aggiornamento Distinta Base — Generazione OF

## Scoperta: gli articoli componenti hanno fornitore e prezzo associati

Esempio testato: articolo RIVSANTOS27 (Tessuto Santos col.27)
- cod_fornitore: [[1, "601.00642"]] — fornitore associato
- prz_riordino: [[1, 21.84]] — prezzo di acquisto
- cod_natura: "MPT" (Materia Prima Tessuto)
- um_principale: "MT"

Questo permette di generare automaticamente gli OF dalla distinta base!

## Flusso generazione OF dalla Distinta Base

### Step 1: Sviluppo distinta (già implementato)
POST /servizi con cmd=sviluppo_distinta_base → lista componenti_sviluppati

### Step 2: Arricchimento componenti (NUOVO)
Per ogni componente con tp_articolo="A" (materiale da acquistare):
- GET /risorse/articoli/CODICE_COMPONENTE
- Leggere: cod_fornitore, prz_riordino, um_principale, descrizione

### Step 3: Raggruppamento per fornitore (NUOVO)
Raggruppare i componenti per cod_fornitore.
Mostrare all'operatore una vista per fornitore:
```
Fornitore 601.00642 — NOME FORNITORE
  - RIVSANTOS27: Tessuto Santos col.27 — 6 MT × 21.84 €/MT = 131.04 €
  - FODSOFABLE: Fodera Sofable — 4.5 MT × XX €/MT = XX €
  Totale OF: XXX €
  [Genera OF]

Fornitore 601.00XXX — ALTRO FORNITORE
  - GOMBOBBRA: Gomma bracciolo — 1 NR × XX €
  [Genera OF]
```

### Step 4: Creazione OF (NUOVO)
Per ogni fornitore, bottone "Genera OF" che crea:

```
POST /risorse/documenti/ordini-fornitori
Header: Azienda=SUT Anno=2026

{
  "sigla": "OF",
  "serie": 1,
  "numero": 0,
  "data_documento": "20260327",
  "cod_conto": "601.00642",
  "id_riga": [[1,1],[2,2]],
  "tp_riga": [[1,"R"],[2,"R"]],
  "codice_articolo": [[1,"RIVSANTOS27"],[2,"FODSOFABLE"]],
  "quantita": [[1,6],[2,4.5]],
  "prezzo": [[1,21.84],[2,XX]],
  "cod_iva": [[1,"22"],[2,"22"]]
}
```

NOTA: i campi OF sono IDENTICI a OC e BF (testato con info=true):
- sigla, serie, numero (0=AUTO)
- cod_conto (codice FORNITORE 601.xxxxx)
- data_documento, codice_articolo, quantita, prezzo, cod_iva

### Step 5: Feedback
Dopo creazione OF mostrare:
- OF creato: OF+1+NUMERO per fornitore NOME
- Link per cancellare (DELETE /documenti/ordini-fornitori/OF+1+NUMERO)

## Componenti da ESCLUDERE dalla generazione OF

NON generare OF per componenti con:
- tp_articolo="L" (Lavorazioni — sono tempo/manodopera, non materiali)
- tp_articolo="S" (Spese — es: minuterie, gestite diversamente)

Generare OF SOLO per tp_articolo="A" (Articoli/materiali da acquistare).

## Interfaccia aggiornata pagina Distinta Base

La pagina 5_🔧_Distinta_Base.py deve avere:

### Sezione 1: Ricerca e simulazione (già presente)
- Cerca articolo PF, simula sviluppo distinta

### Sezione 2: Vista per fase (già presente)
- Componenti raggruppati per fase con colori per tipo

### Sezione 3: Generazione OF (NUOVA)
- Sotto la vista per fase, sezione "Genera ordini fornitore"
- Per ogni componente tp_articolo="A", chiama GET /articoli/CODICE per leggere fornitore e prezzo
- Raggruppa per fornitore
- Mostra una card per fornitore con lista materiali, quantità, prezzi, totale
- Bottone "Genera OF" per ogni fornitore
- Bottone "Genera tutti gli OF" per crearli tutti in un colpo
- Dopo creazione: mostra numero OF assegnato e bottone annulla

### Note per lookup fornitore
Per avere il nome del fornitore:
GET /risorse/fornitori/601.00642
Campo: ragione_sociale

## Campi articolo componente utili
| Campo | Descrizione | Uso |
|---|---|---|
| cod_fornitore | Array [[1, "601.xxxxx"]] | Fornitore per l'OF |
| prz_riordino | Array [[1, prezzo]] | Prezzo unitario per l'OF |
| um_principale | "MT", "MQ", "NR" | UM per display |
| descrizione + descrizione_agg | Testo | Descrizione completa |
| cod_natura | "MPT", "ACC", etc | Tipo materiale |
| alq_iva | "22" | Aliquota IVA per l'OF |
