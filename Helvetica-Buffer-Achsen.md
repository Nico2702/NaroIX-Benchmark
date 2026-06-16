# Helvetica — Rang-Buffer (8/13) vs. Coverage-Buffer (±5/±0,5)

Warum die beiden Buffer-Regeln **nicht austauschbar** sind und warum die Rang-Band-Regel (8/13)
für Helvetica essenziell ist.

## Die zwei Buffer wirken auf verschiedenen Achsen

| Buffer | stabilisiert | relevant für |
|---|---|---|
| **8/13** | die **Rang-10-Grenze** (wer von den Kandidaten holt sich die 10 Plätze) | **fixe Anzahl** (Helvetica 10/10/10) |
| **±5/±0,5** | die **Segment-Grenze** (70/85/99-Coverage-Übergang, also das Label) | **variable Anzahl** (Coverage-Index, z. B. Global Markets) |

In Helvetica entscheidet sich die Mitgliedschaft **am Rang-10-Schnitt** des Sleeves — nicht an der
Segment-Grenze. Die ±5/±0,5 berührt diesen Rang-10-Schnitt **nicht** (der Large-Sleeve ist top-10
nach Total MCap, segment-agnostisch). Nimmt man die 8/13 weg, ist der Rang-10-Schnitt **komplett
ungepuffert**.

## Konkrete Folge

Ein Titel, der um **Rang 10 ↔ 11** pendelt, würde dann **jede Periode rein- und rausfliegen** — genau
der Churn, den die 8/13 verhindert. Die ±5/±0,5 kann das nicht auffangen, weil sie nur das *Label*
(Large/Mid) ändert, nicht die *Top-10-Position*. → **Turnover steigt**, ohne Gegenwert.

## Der eigentliche Punkt

Die beiden Regeln sind **nicht austauschbar**, weil sie für **verschiedene Index-Typen** gemacht sind:

- **Variabler Coverage-Index** (Global Markets): keine feste Anzahl → die Segment-Grenze **ist** die
  Mitgliedschaftsgrenze → ±5/±0,5 stabilisiert sie. Hier ist ±5/±0,5 das richtige (und einzige nötige)
  Werkzeug.
- **Fixzahliger Index** (Helvetica 10/10/10): die Mitgliedschaft entscheidet sich am **Rang-10-Schnitt**
  → es braucht zwingend einen **Rang-Buffer** (8/13). Ein reiner Coverage-Buffer lässt den
  Count-Schnitt offen.

Deshalb: ±5/±0,5 **statt** 8/13 würde Helvetica seinen einzigen wirksamen Turnover-Schutz nehmen.

## Der Top-10-Deckel verschiebt die bindende Grenze

Der tiefere Grund: Helveticas Sleeves schöpfen zwar aus den Coverage-Segmenten (Large-/Mid-/Small-
Coverage-Index) — aber durch den **Top-10-Deckel** wandert die *bindende* Grenze von der
Coverage-Grenze zum Rang-10-Schnitt.

| | Global Markets (Coverage-Index) | Helvetica (Top-10-Sleeve) |
|---|---|---|
| Mitglieder im Large | **alle** mit Coverage < 70 % | **nur die Top-10** davon |
| **Bindende Grenze** | die **70 %-Coverage-Grenze** | der **Rang-10-Schnitt** |
| Richtiger Buffer | **±5/±0,5** | **8/13** |

Entscheidend: Ein Titel, der die 70 %-Grenze überquert, ändert sein **Label** (Large ↔ Mid) — aber
**nicht seinen Total-MCap-Rang**. Der Top-10-Schnitt läuft nach **Rang**, nicht nach Label. Also bewegt
die ±5/±0,5 einen Titel **nicht** in die Top-10 hinein oder hinaus:

- Großer Titel (Rang ≤ 8): im Large-Sleeve, egal ob Label Large oder Mid.
- Grenz-Titel (Rang ~10): entscheidet die **8/13**, nicht das Coverage-Label.

> **Präzisierung:** Das gilt exakt für den **Large-Sleeve** (segment-agnostische Top-10). Im **Mid/Small**-
> Sleeve ändert die ±5/±0,5 sehr wohl die *Zusammensetzung* (~4–8 Namen/Periode), weil ein
> „Large"-gelabelter Titel aus dem Mid-Sleeve **ausgeschlossen** wird. Die **Turnover-Rate** bleibt
> dabei gleich (gleiche Zahl Eintritte). Genau dieses gewollte Verhalten nutzt die Sub-Index-Methodik:
> jeder Sleeve zieht strikt aus seinem Sub-Index.

Ohne Deckel (Global Markets) bleibt die Coverage-Grenze die Mitgliedschaftsgrenze → ±5/±0,5 ist dort
das richtige Werkzeug. Mit Deckel (Helvetica) ist es der Rang-10-Schnitt → 8/13.

## Beleg aus der Simulation (48 Perioden, Equity-Eintritte)

| Variante | Buffer | Turnover | vs. „kein Buffer" |
|---|---|---|---|
| A (aktuell) | **8/13** | **53** | **−28 %** |
| C | nur ±5/±0,5 (ohne 8/13) | 69 | −7 % |
| D (Referenz) | kein Buffer | 74 | — |

Würde die ±5/±0,5 die *bindende* Grenze stabilisieren, müsste sie den Turnover senken. Sie liegt aber
mit −7 % praktisch auf „kein Buffer"-Niveau, während die 8/13 **−28 %** bringt. 8/13 durch ±5/±0,5 zu
ersetzen erhöht den Turnover um **+30 %** (53 → 69).

## Fazit

- **8/13 behalten** ist für eine fixe 10/10/10-Struktur essenziell.
- **±5/±0,5 ersetzt das nicht** — sie ist das Werkzeug für variable Coverage-Indizes.
