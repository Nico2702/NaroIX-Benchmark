# NX-EU-LM: Warum 53 europäische Titel fehlen

**Analyse · Stand 2026-08-18 · Stichtag 2026-05-20 · Multi-Period über 47 Perioden**

> **Datenbasis korrigiert.** Die Läufe liefen zunächst versehentlich auf
> `NaroIX_ACWI_Selection_Master_05_2026_Final.xlsx` (48 Perioden), weil die Skripte den
> alphabetisch ersten Master griffen. Maßgeblich ist
> `..._New_v3_ohne01012025_FESTWERTE.xlsx` (47 Perioden). Die Kernzahlen in Abschnitt 3 sind
> mit der richtigen Datei nachgerechnet. Die Detailtabellen zur letzten Periode bleiben gültig:
> beide Dateien unterscheiden sich dort um 0,14 % in der Total MCap und liefern identische
> Zeilen- und ISIN-Zahlen.

Vier komplette Pipeline-Läufe, jeweils 48 Perioden mit fortgeschriebenem Incumbent-State:
Segmentierung je Land und mit Europa-Pooling, je einmal mit symmetrischem Size-Buffer und
einmal mit "Aufstieg am Cut-off". Settings: EUMSS-Floor an, Min FF 10 %, ADTV DM 2 Mio USD,
Buffer Rules an (Coverage 90), Size Buffer 5 pp.

---

## Zusammenfassung

51 der 53 Titel liegen im investierbaren Universum und bestehen **jeden** Screen. Sie fehlen
ausschließlich, weil die Coverage-Segmentierung **je Land** rechnet und sie damit in ihrem
Heimatmarkt hinter die 85-Prozent-Linie fallen. Die Folge ist eine Größen-Inversion zwischen
den Märkten: 119 der 362 Indexmitglieder sind kleiner als der größte fehlende Titel.

Die neue Buffer-Regel behebt das **nicht** (0 von 53 in der letzten Periode). Wirksam ist nur
das Europa-Pooling, und am stärksten in Kombination mit der neuen Regel: 26 von 53.

---

## 1. Es ist kein Filter-Problem

| Stufe | Ausfälle aus der Liste |
|---|---|
| Nicht im Master-Snapshot | 2 |
| Universe-Screens (Preis, Exclusions, Klassifikation) | 0 |
| EUMSS-Größen-Floor / Min FF % | 0 |
| Liquidität (ADTV + ATVR, dual horizon) | 0 |
| Ineligible-Liste | 0 |
| **Segment = Small Cap (Coverage ≥ 85 %)** | **51** |

Alle 51 sind liquide, groß genug für den EUMSS-Floor und haben einen ausreichenden Streubesitz.
Es fehlt kein einziger wegen eines Investierbarkeits-Kriteriums.

**Coverage-Lage der 51 Titel:** 86 bis 88 % → 5 Titel · 88 bis 90 % → 6 · 90 bis 92 % → 17 ·
92 bis 95 % → 16 · 95 bis 100 % → 7. Nur 11 liegen unter der 90-Prozent-Kante, die der
Incumbent-Coverage-Buffer überhaupt erreichen könnte.

**Größe:** 6,14 bis 19,09 Mrd USD Full MCap, Median 10,68 Mrd.
**Herkunft:** Frankreich 16, Deutschland 13, Schweiz 8, Spanien 6, Niederlande 6, Dänemark 2.

---

## 2. Die Größen-Inversion zwischen den Märkten

Der implizite Standard-Cutoff, also die kleinste Full MCap, die es je Land in den Index schafft:

| Markt | Titel im Index | Cutoff | fehlen aus der Liste |
|---|---|---|---|
| Polen | 16 | **4,73 Mrd** | 0 |
| Schweden | 50 | 5,48 | 0 |
| Norwegen | 17 | 5,79 | 0 |
| Belgien | 13 | 6,22 | 0 |
| Finnland | 14 | 8,10 | 0 |
| Vereinigtes Königreich | 65 | 8,48 | 0 |
| Österreich | 8 | 8,94 | 0 |
| Italien | 24 | 11,68 | 0 |
| Portugal | 4 | 13,85 | 0 |
| Irland | 6 | 13,98 | 0 |
| Dänemark | 13 | 14,62 | 2 |
| Deutschland | 39 | 15,42 | 13 |
| Frankreich | 32 | 17,27 | 16 |
| Schweiz | 31 | 17,87 | 8 |
| Niederlande | 17 | 20,63 | 6 |
| Spanien | 13 | **23,04 Mrd** | 6 |

Die Spanne beträgt Faktor 4,9. **Alle 51 fehlenden Titel kommen aus den sechs Märkten mit den
höchsten Cutoffs. Aus den zehn Märkten mit niedrigeren Cutoffs fehlt kein einziger.**

Die kleinsten Indexmitglieder:

| Titel | Markt | Full MCap | Coverage |
|---|---|---|---|
| Budimex | Polen | 4,73 Mrd | 85,0 % |
| Holmen B | Schweden | 5,48 | 89,2 % |
| Getinge B | Schweden | 5,74 | 87,9 % |
| Vend Marketplaces | Norwegen | 5,79 | 79,2 % |
| Wallenius Wilhelmsen | Norwegen | 5,85 | 78,6 % |

Dagegen fehlt Knorr-Bremse mit 19,09 Mrd, also dem Vierfachen von Budimex.

**Wichtig: innerhalb eines Marktes ist die Reihenfolge korrekt.** In Frankreich liegt der
kleinste Indextitel bei 17,27 Mrd, der größte fehlende bei 16,27 Mrd. In der Schweiz 17,87
gegen 17,74. Es ist also kein Sortier- oder Rechenfehler, sondern die zwangsläufige Folge davon,
dass jeder Markt seine eigene 85-Prozent-Linie bekommt.

---

## 3. Wirkung der vier Varianten

Letzte Periode 2026-05-20:

| Variante | Indexgröße (letzte) | Bestand Ø | Turnover Ø | aus der Liste drin |
|---|---|---|---|---|
| je Land, symmetrisch (IST) | 359 | 319,3 | 11,6 | **0 von 53** |
| Europa gepoolt, symmetrisch | 311 | 284,1 | 8,7 | 12 von 53 |
| **Europa gepoolt, Aufstieg am Cut-off** | 350 | 326,7 | 13,0 | **26 von 53** |

(Werte mit der v3-FESTWERTE-Datei. Der Lauf "je Land, Aufstieg am Cut-off" ist damit noch nicht
nachgerechnet, er lag auf der alten Datei bei 398 Titeln und ebenfalls 0 von 53.)

Über alle Perioden, Zahl der Titel, die **nie** in den Index kommen (Werte von der alten
Datei, Größenordnung belastbar): symmetrisch 35, Cut-off 27, gepoolt-symmetrisch 24, gepoolt
mit Cut-off nur noch 8.

### Warum die neue Buffer-Regel hier nichts bewirkt

Sie verschiebt die Aufstiegsschwelle für Bestandstitel von 80 auf 85 Prozent Coverage. Alle 51
Titel liegen aber **über** 85 Prozent. Die Regel greift also strukturell nicht bei ihnen. Über
die Historie steigt der Schnitt zwar von 7,6 auf 10,1 Titel, weil einzelne zeitweise unter die
Kante rutschen, in der letzten Periode ist der Effekt null.

Bemerkenswert: die Variante "je Land, Aufstieg am Cut-off" hat mit 398 Titeln den **größten**
Index, holt aber keinen einzigen der gesuchten Titel. Sie fügt Titel aus Märkten mit niedrigem
Cutoff hinzu, also genau dort, wo der Index schon vergleichsweise tief reicht.

### Warum Pooling wirkt

Der gemeinsame Europa-Cutoff liegt bei rund 9 bis 10 Mrd statt bei 15 bis 23 Mrd in den großen
Märkten. Damit sinkt die Coverage-Position der betroffenen Titel um 3 bis 7 Punkte:

| Titel | Coverage je Land | Coverage im Pool |
|---|---|---|
| Knorr-Bremse | 87,9 % | **81,4 %** |
| Euronext | 89,5 % | 82,3 % |
| Julius Bär | 87,6 % | 82,4 % |
| Carrefour | 87,4 % | 84,7 % |
| Renault | 92,1 % | 89,6 % |

Erst dadurch geraten sie in den Bereich, in dem Segmentierung und Buffer sie erfassen können.
Pooling und neue Buffer-Regel wirken zusammen: Pooling allein holt 12, die Regel allein 0,
beides zusammen 26. Das ist ein Interaktionseffekt, keine Addition.

Die 22 Rückkehrer bei gepoolt und Cut-off: Knorr-Bremse, Euronext, Julius Bär, EDP Renewables,
Unibail-Rodamco, ASR Nederland, Acciona, Ipsen, Mapfre, Carrefour, Bankinter, Eiffage, Swatch,
Banque Cantonale Vaudoise, Eurofins, Accor, Symrise, BELIMO, Getlink, Akzo Nobel, Renault,
Redeia.

---

## 4. Was auch dann draußen bleibt

29 Titel, Full MCap 6,14 bis 13,51 Mrd (Median 9,06), Coverage im Europa-Pool 86,0 bis 93,3 %
(Median 90,1 %). Die größten davon: Swiss Prime Site (13,51), Rexel (12,52), HENSOLDT (11,78),
Klepierre (11,55), Delivery Hero (11,39), Lufthansa (11,07), Indra (10,68), GEA (10,45).

Diese Titel liegen auch im gesamteuropäischen Maßstab hinter der 85-Prozent-Linie. Sie über eine
Coverage-Regel zu holen, würde bedeuten, die Standard-Grenze für ganz Europa nach hinten zu
verschieben, also den Index insgesamt deutlich zu vergrößern.

---

## 5. Die zwei nicht gefundenen ISINs

| gelistet | im Master | Befund |
|---|---|---|
| DK0060738590 | **DK0060738599** (Demant A/S, 7,86 Mrd) | Zifferndreher an der letzten Stelle. Der Titel existiert und ist Small Cap, denn der dänische Cutoff liegt bei 14,62 Mrd |
| FR0013028286 | nicht vorhanden | keine ISIN mit Präfix FR001302 im Master, Quelle prüfen |

---

## 6. Konsequenzen

1. **Die Liste ist kein Qualitätsproblem der Screens.** Sie ist die direkte Folge der
   länderweisen Coverage-Segmentierung. Wer sie schließen will, muss an der Segmentierungs-Achse
   ansetzen, nicht an den Filtern.
2. **Die Buffer-Diskussion und diese Liste sind zwei verschiedene Themen.** Die neue Regel
   beseitigt die Benachteiligung von Bestandstiteln, sie holt aber keinen der hier gesuchten
   Titel. Beide Maßnahmen sind unabhängig zu bewerten.
3. **Europa-Pooling ist der einzige gemessene Hebel mit substanzieller Wirkung**, und zwar
   entgegen der ersten Einschätzung: es verkleinert den Index (317 gegen 362), verschiebt seine
   Zusammensetzung aber genau in Richtung der hier fehlenden Titel. Wer die Überschneidung mit
   MSCI Europe als Ziel nimmt, sollte Pooling als Hauptkandidaten prüfen, nicht die
   Größen-Zusatzregeln.
4. **Größenschwellen greifen hier nicht.** Eine globale Schwelle (T = 19,3 Mrd) erfasst keinen
   der 51 Titel, eine länderrelative Schwelle (2/3 des Länder-Cutoffs) erfasst 11.

*Rohdaten: mp_want.csv, mp_want_pool.csv, mp_members_sym.csv, mp_members_cut.csv,
mp_members_pool_sym.csv, mp_members_pool_cut.csv im Scratchpad.*

---

# Teil 2: Die Fehlliste im gepoolten Lauf (44 Titel)

Zweite Liste, erhoben gegen den Europa-Pool-Lauf. Die Zahlen dieses Teils stammen noch aus
den Läufen auf der alten Master-Datei, die Richtung und Größenordnung sind belastbar, die
Einzelzählungen können um wenige Titel abweichen. 43 der 44 sind im Master (BE0003832409
fehlt). Alle 43 sind auch hier **Small Cap**, keiner scheitert an einem Screen.

## Die Liste zerfällt in zwei Gruppen

| Gruppe | Anzahl | Märkte |
|---|---|---|
| **Verlierer des Poolings** (waren je Land im Index) | **17** | Schweden 9, UK 3, Norwegen 2, Belgien 2, Finnland 1 |
| Auch vorher schon draußen | 26 | Frankreich 6, Deutschland 5, UK 4, Dänemark 3, Niederlande 3, Schweiz 2, Italien 2, Spanien 1 |

Die zweite Gruppe überschneidet sich mit den 29 Titeln aus Teil 1, die auch gepoolt nicht
hereinkommen. Neu und erklärungsbedürftig ist nur die erste Gruppe.

## Warum das Pooling diese 17 verliert

Der gepoolte Standard-Cutoff ist **eine** Linie bei 9,32 Mrd USD, an die Stelle von sechzehn
Länderlinien zwischen 4,73 und 23,04 Mrd. Märkte, deren eigene Linie unter 9,32 lag, verlieren
damit ihren unteren Rand:

| | je Land | gepoolt |
|---|---|---|
| Schweden | 5,48 Mrd | 9,32 Mrd |
| Norwegen | 5,79 | 9,32 |
| Belgien | 6,22 | 9,32 |
| Finnland | 8,10 | 9,32 |
| UK | 8,48 | 9,32 |

Gesamtbilanz des Poolings in der letzten Periode: **33 Titel kommen herein** (9,32 bis 27,46 Mrd,
Median 14,84), **78 fallen heraus** (4,73 bis 18,80 Mrd, Median 9,91). Netto 362 → 317.

Verlierer nach Markt: Schweden 21, Polen 11, Norwegen 10, UK 10, Belgien 9, Finnland 5,
Österreich 5, Italien 4, Dänemark, Irland, Portugal je 1.
Gewinner nach Markt: Schweiz 13, Frankreich 7, Niederlande 6, Spanien 4, Deutschland 3.

## Was dabei besser wird

Die Größen-Inversion schrumpft deutlich:

| | Anteil der Indexmitglieder, die kleiner sind als der größte Fehlende |
|---|---|
| je Land | **33 %** (119 von 362) |
| gepoolt | **7 %** (21 von 317) |

Der Überschneidungsbereich schrumpft von 4,73 bis 19,09 Mrd auf 9,32 bis 13,01 Mrd. Gemessen an
der Größenkonsistenz ist der gepoolte Index also klar sauberer, er ist nur kleiner.

## Die verbleibende Überschneidung ist kein Float-Effekt

Naheliegend wäre, die restlichen 7 Prozent mit unterschiedlichem Streubesitz zu erklären. Das
trägt nicht:

| Titel | Full MCap | Adj FF | Float-Anteil | Status |
|---|---|---|---|---|
| Rexel | 12,52 Mrd | 12,27 | 98,0 % | **draußen** |
| Var Energi | 13,01 | 4,56 | 35,0 % | draußen |
| Klarna Group | 9,56 | 1,99 | **20,8 %** | **im Index** |
| Redeia | 9,32 | 7,08 | 75,9 % | im Index |

Rexel hat den höchsten Float der ganzen Gruppe und ist draußen, Klarna den niedrigsten und ist
drin. Die Ursache ist die **Buffer-Historie**: Redeia ist Mid-Incumbent und wird bis 90 Prozent
Coverage gehalten, Rexel ist Small-Incumbent und müsste unter 80 (symmetrisch) beziehungsweise
85 Prozent (Aufstieg am Cut-off) fallen, liegt aber bei 86,7 Prozent. Dieselbe Pfadabhängigkeit,
die wir an der Mid-Small-Kante diskutiert haben, nur diesmal im gepoolten Universum.

## Fazit Teil 2

Die zweite Fehlliste ist überwiegend der **Preis** des Poolings, nicht ein weiterer Fehler.
Pooling tauscht 78 kleinere Titel aus Märkten mit niedriger Linie gegen 33 größere aus Märkten
mit hoher Linie. Das Ergebnis ist ein kleinerer, aber größenkonsistenterer Index. Die Frage ist
damit nicht mehr technisch, sondern eine Produktentscheidung: Soll die Standardgrenze für ganz
Europa einheitlich gelten, mit dem Verlust der schwedischen, norwegischen, belgischen und
finnischen Mittelschicht, oder soll jeder Markt seine eigene Tiefe behalten, mit der Folge, dass
ein deutscher 19-Mrd-Titel fehlt, während ein polnischer 4,7-Mrd-Titel dabei ist.
