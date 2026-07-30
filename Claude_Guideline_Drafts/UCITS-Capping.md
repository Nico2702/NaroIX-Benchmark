# UCITS / Capping — Konzept-Notiz (geparkt)

**Status:** Diskussion 2026-07-15, geparkt, wir kommen später darauf zurück. Noch KEINE
Entscheidung getroffen, noch NICHT im Code umgesetzt.

Kontext: mögliches Weight-Capping für die NaroIX Global Index Series (Region×Size:
GM / DM / EM / EU × L / M / S / LM / AC / TM). Rein Guideline-/Methodik-Ebene.

---

## 1. Grundsatz-Empfehlung: selektiv, nicht für alle

- **Breite Indizes (GM, DM Standard, All Cap, Total Markets):** kein Capping. Kein Name
  dominiert (größte Einzelgewichte ~4 bis 5%), ein Cap greift praktisch nie und würde nur
  das Dokument verkomplizieren. Ein Basis-Benchmark soll den Markt ungecappt abbilden.
- **Capping sinnvoll bei:** konzentrierten / schmalen Indizes (Einzelland, ggf. Europe,
  Small-Cap-Segmente) und vor allem den **thematischen** (Tech Top-N, WL-100), sowie
  produkt-/UCITS-getrieben, wenn ein ETF auf den Index UCITS-fähig sein muss.
- **Industrie-Norm (MSCI, Solactive, Morningstar):** nicht den Basis-Index cappen, sondern
  **separate gecappte Varianten** veröffentlichen (eigener Code, Flag in Appendix A).
  Flaggschiffe ungecappt lassen.

Weichenstellung hängt am **Treiber:**
- **UCITS / Produkt** -> produkt-relevante Indizes cappen, typischerweise 5/10/40.
- **Konzentration** -> schmale / thematische Indizes cappen, fixes Issuer-Cap.

---

## 2. Empfohlene Capping-Regel (Default): UCITS 5/10/40, Issuer-Level

An jedem Selection Day, nach der Float-Gewichtung:

1. **10%-Cap:** kein einzelner Emittent > 10%. Überschuss pro-rata auf die
   nicht-gedeckelten Titel umverteilen.
2. **40%-Aggregat:** die Summe aller Emittenten mit Gewicht > 5% darf 40% nicht
   überschreiten. Wenn doch, die > 5%-Positionen (größte zuerst oder pro-rata) reduzieren,
   bis die Summe ≤ 40%.
3. **Iterieren**, bis beide Bedingungen gelten und die Gewichte auf 100% normiert sind.

**Issuer-Level (wichtig):** da die Serie Mehrfach-Notierungen erlaubt (Variante B), alle
Linien einer Firma (über Entity ID) VOR dem Cap zusammenfassen, sonst umgeht eine Firma den
Cap über zwei Linien.

**Rebalance-Puffer (optional, üblich):** am Rebalance nicht exakt bei 10% / 40% cappen,
sondern mit Headroom (z. B. 9% / 35%), damit die intra-Quartals-Drift die harte
10% / 40%-Grenze nicht sofort reißt. Alternativ hart bei 10% / 40% cappen und die Drift dem
Fonds überlassen (einfacher, engere Grenzen).

### Einfachere Alternative (nicht-UCITS)
Für rein konzentrations-getriebene (thematische / schmale) Indizes reicht ein **fixes
Issuer-Cap**, z. B. jeder Emittent ≤ 10% (nur Schritt 1, ohne 40%-Aggregat). Manche nehmen
4,5% oder 5% für sehr breite Streuung.

---

## 3. Umsetzung (Engine)

- Capping ist ein **Post-Schritt nach der Gewichtsnormierung**, isoliert in `build_index`
  je Index-Slice: Gewichte deckeln, Überschuss pro-rata umverteilen, iterativ bis
  konvergiert. ~20 bis 30 Zeilen, deterministisch, kein Eingriff in Selektion / Segmentierung.
- Steuerung per Index-Flag (Cap-Typ + Level) analog zu anderen INDEX_SERIES-Feldern.
- Aufwand: gering. Risiko: gering (isolierter Schritt).

---

## 4. Wichtige Caveats

- **Gewichte werden ohnehin schon pro Index neu normiert** (Adj_FF_MCap über die jeweilige
  Mitgliedermenge). Das Gewicht eines Titels in NX-GM ≠ sein Gewicht in NX-DM.
- Die Additivität **GM = DM + EM gilt auf Konstituenten-Ebene** (gleiche Mitglieder, gleiche
  Größenklasse, gleiches Adj_FF_MCap; GM-Universum = DM ∪ EM), NICHT als identische Gewichte.
  In Gewichten ist GM die float-gewichtete Kombination von DM und EM.
- **Capping bricht die float-Blend-Beziehung:** ein in DM gedeckelter Titel ist in GM
  (kleiner) evtl. ungedeckelt, dann ist GM nicht mehr der reine float-gewichtete Mix aus
  (gecappten) DM und EM. Deshalb Capping als index-spezifische Regel deklarieren, nicht
  implizieren, dass gecappte Regional-Indizes weiter sauber zu GM aggregieren.

---

## 5. Offene Entscheidungen (bei Wiederaufnahme klären)

1. **Treiber:** konkretes UCITS-Produkt auf einem Index, oder allgemeines
   Konzentrations-Management?
2. **Cap-Typ + Level:** 5/10/40 vs. fixes Issuer-Cap (10% / 5% / 4,5%)?
3. **Rebalance-Puffer** (z. B. 9/35) ja/nein?
4. **Welche Indizes** genau (nur thematische, oder auch Europe / EM / Einzelland)?
5. **Variante vs. In-Place:** eigener gecappter Index-Code neben dem ungecappten (empfohlen)
   oder Cap direkt im bestehenden Index?
6. Guideline-Abschnitt **„Weighting Cap"** + Appendix-A-Flag formulieren.
