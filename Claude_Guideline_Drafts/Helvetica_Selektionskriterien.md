# Swiss-Made Portfolio Index: alle Selektionskriterien inklusive Maintenance

**Index:** Swiss-Made Portfolio Index (intern "Helvetica"), ISIN DE000A4AV9S7, EUR, Net Total Return
**Quelle:** Index Guideline "Swiss-Made Portfolio Index", Version 1.0, Juli 2026
**Währung aller Schwellen:** CHF
**Stand:** 2026-08-12

> **Kurzreferenz.** Die vollständige Bau-Spezifikation mit Datenfeldern, Pseudocode, Randfällen und
> Abnahmetests steht in `Helvetica_Selection_Tool_Spec.md`. Bei Widersprüchen gilt die Guideline.

> **Nicht aus dem Backtest-Code ableiten.** Der Tool-Code in `naroix_benchmark.py` kennt die
> ADTV-Maintenance (Kriterium 5) und den Micro-Fill-up (Kriterium 11) **nicht** und rechnet in USD.
> Er bleibt bewusst so, damit die publizierte Backtest-Historie reproduzierbar bleibt.

---

## 1. Reihenfolge der Kette

Die Reihenfolge ist verbindlich, jeder Schritt arbeitet auf dem Ergebnis des vorherigen.

```
0. Ausschlüsse (inklusive Sanktionslisten)
1. Börse SIX + Free Float MCap > 0
2. Minimum Free Float
3. Liquidität (3M ADTV)
4. Dedup: eine Linie je Firma
5. Coverage-Rechnung (Real Estate BLEIBT im Pool)
6. Size Buckets
7. Equity-Sleeves: Top 10 mit Rang-Band, dann Fill-up
8. Swiss REITs: alle qualifizierten
```

---

## 2. Alle Kriterien, Entry gegen Maintenance

| # | Kriterium | Entry (Neukandidat) | Maintenance (Inkumbent) | Achse |
|---|---|---|---|---|
| 1 | Börse | `Exchange Name == "SIX SWISS"` | keine Lockerung | Titel |
| 2 | Free Float MCap | `> 0` | keine Lockerung | Titel |
| 3 | Closing Price | `< CHF 20 000` | keine Lockerung | Titel |
| 4 | **Minimum Free Float** | `>= 10,0 %` (`0.10`) | **`>= 7,5 %`** (`0.075`) | Titel |
| 5 | **3M ADTV** | `>= CHF 1 000 000` | **`>= CHF 750 000`** | Titel |
| 6 | ADTV-Historie | volle 3 Monate | bei Spin-Off und Mega-IPO: **maximal verfügbarer Zeitraum** | Titel |
| 7 | Sanktionslisten | Ausschluss (EU, SECO, OFAC, UN, OFSI) | keine Lockerung, löst außerordentliches Rebalancing aus | Emittent |
| 8 | Eine Linie je Firma | liquideste Linie (höchstes 3M ADTV) | keine Lockerung | Firma |
| 9 | **Size Bucket** | 70 / 85 / 99 % Coverage | **75 / 90 / 99,5 %** als Hysterese, siehe 3 | **Firma** |
| 10 | **Platz im Sleeve** | Rang **≤ 8** | **Rang ≤ 13** | Titel je Sleeve |
| 11 | Micro Cap | nicht eligible für die Equity-Sleeves | nur als **Fill-up** in den Small-Sleeve | Titel |

**Zusätzlich, aus der Engine-Hygiene und nicht aus der Guideline, ohne Maintenance:** kein Name mit
`ETF`, `SICAV` oder `%`, kein delisteter Titel (`Listing Status == 1`), kein
`Country of Risk == "@NA"`. Diese Filter widersprechen der Guideline nicht, sollten aber im
Parameterprotokoll ausgewiesen werden.

Der frühere Fondsausschluss über `NAICS` ("Open-End Investment Fund") ist am 2026-08-23 entfallen,
weil das FactSet-Feld überwiegend operative Asset Manager als Fonds markierte. Im Master 05/2026
traf die Regel keinen einzigen Schweizer Titel, für Helvetica ändert sich also nichts.

**Zu Kriterium 6:** Mega-IPO ist definiert als Neuemission, Direct Listing, Transfer Listing oder neu
gelistetes Depositary Receipt mit einer Total Market Capitalization von mindestens **USD 100 Mrd.**
Die Schwelle steht in der Guideline in USD, während alle anderen Kriterien in CHF stehen. Das ist so
übernommen und nicht umzurechnen.

---

## 3. Kriterium 9 im Detail: Size Buckets

| Bucket | Entry | Maintenance-Band | Herleitung |
|---|---|---|---|
| Large Cap | `_c_before < 70` | `< 75` | 70 + 5 |
| Mid Cap | `70 bis 85` | `65 bis 90` | 70 − 5 bis 85 + 5 |
| Small Cap | `85 bis 99` | `84,5 bis 99,5` | 85 − 0,5 bis 99 + 0,5 |
| Micro Cap | `>= 99` | keine | Rest |

Vier Punkte, die exakt so gelten:

1. **Straddle Rule:** `_c_before` ist die kumulierte Coverage **vor** der eigenen Zeile. Ein Titel, der
   eine Schwelle überschreitet, geht in den **größeren** Bucket.
2. **Zwei verschiedene Größen:** sortiert wird nach **Total MCap** (Tiebreaker Free Float MCap),
   kumuliert wird **Free Float MCap**.
3. **Real Estate bleibt im Nenner.** RE-Titel zählen in Sortierung, Kumulation und Gesamtsumme und
   werden erst **nach** der Bucket-Zuordnung in den REIT-Sleeve überführt. Wer RE vorher herausfiltert,
   bekommt andere Buckets.
4. **Weitester Adressatenkreis:** Dieser Buffer gilt für **jede Firma mit einem Bucket in der
   Vorperiode**, auch wenn sie nie selektiert war. Die anderen Buffer gelten nur für tatsächliche
   Konstituenten.

Die Untergrenzen (Mid ab 65, Small ab 84,5) sind nötig, damit eine echt gewachsene Firma auch
**aufsteigen** kann. Large braucht keine, es ist die oberste Klasse.

---

## 4. Kriterium 10 im Detail: Rang-Band 8 / 13

```
Schritt 1: Rang <= 8            -> fest drin, Bestand oder neu
Schritt 2: Restplätze bis 10    -> an INKUMBENTEN mit Rang 9 bis 13, in Rangfolge
Schritt 3: noch frei            -> beste verbleibende ab Rang 9, in Rangfolge
```

Rang nach **Free Float MCap** (Tiebreaker Total MCap), nur innerhalb des eigenen Buckets. Ein Neuling
muss sich auf **Rang 8** hocharbeiten, ein Bestandstitel darf bis **Rang 13** abrutschen. Diese Lücke
ist der Puffer, und sie ist der wirksamste der vier: bei fixer Titelzahl ist der **Rang-10-Schnitt** die
bindende Grenze, nicht die Coverage-Grenze.

Nebenbedingung: der harte Cut (8) muss **kleiner** als die Sleeve-Größe (10) sein, sonst bleibt kein
Platz reserviert und der Buffer ist wirkungslos.

---

## 5. Kriterium 11 im Detail: Fill-up

Reicht ein Bucket nicht für 10 Titel, zieht der Sleeve aus den **kleineren** Buckets nach, sortiert nach
Free Float MCap. Der Fill-up läuft **sequenziell von oben** (Large, dann Mid, dann Small), und gewählte
Titel werden aus dem Restbestand entfernt, bevor der nächste Sleeve dran ist. Die 10er-Prüfung des
nächsten Sleeves läuft also auf dem **reduzierten** Bestand, wodurch sich die Kaskade fortpflanzt.

* **Quelle sind alle kleineren Buckets, nicht nur das nächstkleinere.** Ein Small-Titel kann direkt in
  den Large-Sleeve rücken, wenn sein Float-MCap höher ist als der der verbleibenden Mid-Titel.
  Belegt am 2016-02-17, dort steht ein `Large <- Small` im Lauf.
* **Kein Übertrag nach unten:** Hat ein Bucket mehr als 10 Titel, nimmt es seine Top 10, der Überschuss
  wird **verworfen** und wandert nicht in den kleineren Sleeve.
* **Micro Cap ist ausschließlich Fill-up-Quelle für Small**, niemals Kern-Konstituent.
* Ein Fill-up-Titel behält seine echte Größenklasse im Reporting (`True_Segment`, `Status = Aufrücker`)
  und erhält das normale Sleeve-Gewicht.

---

## 6. Was NICHT geschützt ist

Börse, Free Float MCap, Preis, Sanktionen und der Dedup kennen **keine** Maintenance. Ein Titel, der
unter CHF 750.000 ADTV oder unter 7,5 % Free Float fällt, ist draußen, egal wie weit oben er im Sleeve
stand. Und der **Dedup** kann einem Inkumbenten den Platz nehmen, wenn eine andere Linie derselben
Firma liquider geworden ist.

---

## 7. Was je Sleeve gilt

| | Equity Large / Mid / Small | Swiss REITs |
|---|---|---|
| Kriterien 1 bis 8 | ja, identisch | ja, identisch |
| Size Bucket (9) | ja | **nein**, keine Segmentierung |
| Rang-Band (10) | ja | **nein**, kein Top-N, also keine Rangkante |
| Auswahl | **Top 10** je Bucket | **alle** qualifizierten, auch in Micro-Größe |
| Gewicht | 10 % / 15 % / 15 % je Sleeve, gleichgewichtet | 15 % / n |
| Bestandsschutz | Free Float, ADTV, Bucket-Hysterese, Rang-Band | Free Float und ADTV |

---

## 8. Seed-Periode

Ohne Bestand greift **kein** Maintenance-Kriterium: Free Float 10 %, ADTV CHF 1,0 Mio., harte Buckets
70 / 85 / 99, Auswahl als schlichte Top 10. Erst ab der zweiten Periode gibt es Inkumbenten. Das ist
explizit zu implementieren und nicht implizit über "leere Menge liefert schon das Richtige".

---

## 9. Matching-Schlüssel und Bezugspunkt

| Kriterium | Schlüssel |
|---|---|
| 4 Free Float, 5 ADTV, 10 Rang-Band | **normalisierte ISIN** des Titels (getrimmt, Großbuchstaben) |
| 9 Size Bucket | **Entity ID** der Firma |
| 8 Dedup | Entity ID, Fallback `"ISIN::" + ISIN` |

Ein Titel kann Inkumbent sein, ohne dass seine Firma einen Vorperioden-Bucket hat, und umgekehrt.
**Inkumbent** bezieht sich auf den Stand **nach dem letzten Rebalancing**, nicht auf den letzten
Selection Day.

---

## 10. Termine

| | Regel |
|---|---|
| Frequenz | quartalsweise |
| Selection Day | Schluss des **3. Mittwochs** im Februar, Mai, August, November |
| Rebalancing Day | Schluss des **1. Mittwochs** im März, Juni, September, Dezember |
| Datenstand | Selektion auf Daten des Selection Day |
| Wirksamkeit | Zielgewichte werden zum Schluss des Rebalancing Day wirksam |

Außerordentliches Rebalancing ist außerhalb des Rhythmus möglich, unter anderem bei Sanktionslistung,
Delisting oder einem Corporate Event, nach dem eine Komponente die Kriterien nicht mehr erfüllt.

---

## 11. Nicht selektiert, sondern fix gesetzt: 45 %

| Sleeve | Instrument | ISIN | Gewicht |
|---|---|---|---|
| Cash (CHF) | CHF-Kassaposition im Index | keine | 5,0 % |
| Swiss Government Bonds | iShares Swiss Domestic Government Bond 3-7 ETF (CH) | CH0016999846 | 5,0 % |
| Swiss Government Bonds | iShares Swiss Domestic Government Bond 7-15 ETF (CH) | CH0016999861 | 5,0 % |
| Swiss Corporate Bonds | iShares Core CHF Corporate Bond ETF (CH) | CH0226976816 | 15,0 % |
| Gold | Amundi Physical Gold ETC | FR0013416716 | 7,5 % |
| Gold | Xtrackers Physical Gold ETC | DE000A1E0HR8 | 7,5 % |

Keine Titelselektion, kein Buffer, kein Coverage-Cut. Zusammen mit den 55 % selektiert (Equity 40 % +
REITs 15 %) ergibt das 100 %.

---

## 12. Geprüfte Wirkung der drei jüngsten Klarstellungen

Nachgerechnet über alle 47 Selection Dates des Masters
`NaroIX_Helvetica_Selection_Master_Final_05_2026_OFFICIAL.xlsx` (2014-11-19 bis 2026-05-20, Daten in
CHF), mit vollem Maintenance-Paket:

| Klarstellung | Wirkung auf die Historie |
|---|---|
| **Börse auf `SIX SWISS`** statt Land = Schweiz | **keine.** 0 von 47 Perioden unterschiedlich, Universe-Differenz 0. Die einzige Nicht-SIX-Zeile (BERNE) fällt ohnehin an anderen Filtern aus |
| **ADTV-Maintenance CHF 750.000** | **4 von 47 Perioden**, ausschließlich REITs: Intershop Holding (2021-02-17) und Peach Property Group (2022-02-16, 2022-05-18, 2022-08-17). Eintritte gesamt unverändert (58), der Buffer **verzögert Austritte**. Wichtig: n_REIT steigt von 4 auf 5, damit sinkt das Gewicht je REIT von 3,75 % auf 3,00 %, also ändern sich in diesen Perioden die Gewichte **aller** REITs |
| **Micro als Fill-up für Small** | **keine.** 0 von 47 Perioden. Der Small-Bucket hat nach Abzug von Large und Mid immer mindestens 10 eigene Titel. Die Regel ist Guideline-Konformität ohne Rückwirkung |

Zum Vergleich, wie aktiv die Kaskade sonst ist: **40 von 47 Perioden** haben Fill-ups, 2014 bis zu 11
(5 mal Large aus Mid, 6 mal Mid aus Small). Ab 2024-11-20 sind es null, der Schweizer Markt hat
inzwischen genug echte Large Caps.
