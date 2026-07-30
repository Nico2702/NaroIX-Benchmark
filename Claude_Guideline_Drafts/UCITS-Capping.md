# UCITS / Capping — Konzept-Notiz

**Status:** Diskussion 2026-07-15, umgesetzt 2026-07-30. Entscheidung: UCITS 5/10/40 auf
Issuer-Level als **optionaler Overlay, per Default AUS**, verfügbar **nur für die sechs
thematischen Tech-Indizes** (NX-US-T100, NX-US-T, NX-EU-T, NX-EU-T30, NX-GM-T500, NX-GM-T100),
**ohne** Rebalance-Puffer, **in-place** (kein separater gecappter Code). Die breiten
Markt-Indizes (GM / DM / EM / EU × Size) bleiben ungecappt.

**Warum Default aus (wichtig):** So wie der Standard-Nasdaq-100 wird der Index **ungecappt
publiziert**. Reale UCITS-ETFs (iShares CNDX, Invesco EQQQ, Xtrackers XNAS) tracken den
Standard-NDX per Vollreplikation; es gibt keine gecappte NDX-Variante am Markt. Die
UCITS-Konformität entsteht auf **Fondsebene** über die Index-Replikations-Ausnahme (Art. 53
UCITS: bis 20% je Emittent, 35% ausnahmsweise; in DE § 209 KAGB Wertpapierindex-OGAW), plus
einmalige Index-Anerkennung durch die Aufsicht beim Fondsaufsatz. Passive Überschreitungen
zwischen Rebalances fallen unter Art. 57(1). Das Index-Capping brauchen wir daher nur, wenn
ein Kunde/Wrapper einen **selbst-konformen** Index verlangt (solche gecappten Varianten gibt
es am Markt, z.B. Nasdaq-100 Capped, MSCI-Capped-Serien).

Umsetzung: `apply_ucits_5_10_40` in `pipeline_core.py`, aufgerufen aus `build_index` je
Index-Slice (Flag `"cap": "5/10/40"` in `INDEX_SERIES`). In der App per Sidebar-Toggle
„Capping" (Default **aus**) als Research-/What-if-Hebel steuerbar; der Toggle zeigt an, für
welche Indizes das Capping gilt. Regressionstest: `test_ucits_cap`.

Kontext: Weight-Capping für die NaroIX Global Index Series (Region×Size:
GM / DM / EM / EU × L / M / S / LM / AC / TM) plus thematische Indizes. Rein
Guideline-/Methodik-Ebene.

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

1. **10%-Cap:** kein einzelner Emittent > 10%. Überschuss pro-rata (gewichtsproportional) auf
   die nicht-gedeckelten Titel umverteilen, iteriert bis kein Titel mehr > 10%.
2. **40%-Aggregat:** die Summe aller Emittenten mit Gewicht > 5% darf 40% nicht
   überschreiten. Wenn doch, die **kleinsten** Über-5%-Emittenten zuerst auf genau 5% senken
   (sie verlassen damit die > 5%-Gruppe), bis das Aggregat ≤ 40% ist. Die größten Namen
   bleiben so an der 10%-Kappe (maximale Repräsentativität). Das freigewordene Gewicht fließt
   proportional zum Spielraum in die Titel unter 5% (kein Titel überschreitet dabei 5%).
3. Deterministisch in einem Durchlauf (Schritt 1 iteriert, Schritt 2 einmalig), Gewichte auf
   100% normiert. Beide Bedingungen gelten danach garantiert.

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

## 5. Entscheidungen (getroffen 2026-07-30)

1. **Treiber:** Konzentrations-Management der thematischen Tech-Indizes (top-heavy), mit Blick
   auf die UCITS-Fähigkeit eines möglichen Produkts. Ergebnis: 5/10/40 gewählt.
2. **Cap-Typ + Level:** UCITS **5/10/40** (nicht das einfache fixe Issuer-Cap).
3. **Rebalance-Puffer:** **nein**, hart bei 10% / 40%. Intra-Quartals-Drift bleibt dem Fonds
   überlassen (einfacher, engere Grenzen).
4. **Welche Indizes:** **nur die sechs Tech-Indizes**. Die breiten Markt-Indizes bleiben
   ungecappt.
5. **Variante vs. In-Place:** **In-Place** mit Sidebar-Toggle (**Default aus**). Kein separater
   gecappter Code; der Index wird ungecappt publiziert (UCITS-Konformität auf Fondsebene via
   Art. 53), der Toggle aktiviert das Capping nur als What-if bzw. für gecappte Varianten.
6. **Noch offen:** förmlicher Guideline-Abschnitt **„Weighting Cap"** in der Kunden-Guideline.
   Die Methodik ist hier und in `INDEX_SERIES.md` dokumentiert; die Aufnahme in die
   veröffentlichte Guideline steht noch aus.
