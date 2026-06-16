# Rang-Band-Buffer (8/13)

Die **Rang-Band-Buffer 8/13** ist eine Hysterese-Regel, die den Turnover dämpft — sie entscheidet,
**wer** die 10 Sleeve-Plätze bekommt, wenn es mehr Kandidaten als Plätze gibt. „Rang" = Position
nach Größe in der Kandidatenliste (Rang 1 = größter).

## Die Regel (Ziel = 10 Plätze)

Drei Schritte, der Reihe nach:

1. **Rang ≤ 8 (hart):** Die Top 8 sind **immer** drin — egal ob Bestand oder neu.
2. **Restplätze (9 & 10):** zuerst an **Bestandstitel (Inkumbenten)**, die im Band **Rang 9–13** liegen.
3. **Falls dann noch Plätze frei:** mit den **bestplatzierten Neulingen** auffüllen (Rang 9, 10, …).

## Der Kern: asymmetrische Schwelle

- **Rein** kommt ein **neuer** Titel nur, wenn er **Rang ≤ 8** schafft (oder ein Restplatz frei bleibt).
- **Drin bleibt** ein **Bestandstitel**, solange sein Rang **≤ 13** ist.

→ Ein Titel muss sich auf **Rang 8 hocharbeiten**, um reinzukommen, darf aber bis **Rang 13 abrutschen**,
bevor er rausfliegt. Diese Lücke (8 ↔ 13) ist der Puffer.

## Wozu

Ohne Puffer würde ein Titel, der um **Rang 10/11** pendelt, jede Periode rein- und rausspringen →
unnötiger Umschlag/Handelskosten. Mit dem Band bleibt er stabil drin, bis er klar (unter Rang 13)
abfällt.

## Mini-Beispiel (Bestand = letzte Periode)

| Titel | aktueller Rang | Bestand? | drin? | warum |
|---|---|---|---|---|
| A | 3 | – | ✅ | Rang ≤ 8 (hart) |
| B | 9 | ja | ✅ | Inkumbent im Band 9–13 |
| C | 12 | ja | ✅ | Inkumbent im Band (≤ 13) |
| D | 10 | nein | ❌ | Neuling, Rang > 8, Restplätze schon an B/C |
| E | 15 | ja | ❌ | Inkumbent, aber Rang > 13 → raus |

## Wichtig für Helvetica

- Aktiv **nur im Multi-Period** (es braucht „Inkumbenten" = die selektierten Titel der Vorperiode).
  Im Single-Snapshot gibt es keinen Bestand → schlichte Top-10.
- Läuft **pro Sleeve über dessen Kandidatenliste** (eigenes Segment + Fallback-Aufrücker), sodass
  auch der Auffüll-Rand stabilisiert ist.
- Implementiert in `_rank_band_select` (dieselbe Solactive-Logik wie bei den NaroIX-Thematik-Indizes).
