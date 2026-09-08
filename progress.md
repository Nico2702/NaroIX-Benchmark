# progress

Rolling Snapshot des aktuellen Arbeitsstands. Kein Changelog, alte Punkte werden geloescht.

## Aktueller Fokus

ENTSCHIEDEN 2026-09-08 (Nico): `label_before_liquidity` wird auf TRUE gestellt, die
Mid/Small-Haltekante bleibt vorerst bei 90. Der Groessen-Waiver auf den Mindest-Free-Float
kommt mit Anker 2,0 x EUMSS-Boden und ist eingebaut. Die Linienwahl ist geschlossen: echte
Mehrfachnotierungen werden vorgelagert bei FactSet gefiltert.

ENTSCHIEDEN 2026-09-08 (Nico), alles bereits Default in der Sidebar:
- Labeling vor Liquiditaet AN (Checkbox statt Toggle)
- Bodenregel = Rang-Mitnahme (Band 99 bis 99,25) plus Bestandsschutz 0,75 x Boden
- FF-Waiver 2,0 x Boden
- ATVR Entry 5 / 5, Maintenance 2,5 / 2,5, symmetrisch wie der ADTV-Screen
Damit weicht jeder Lauf ohne manuelle Umstellung von allen Messungen vor dem 08.09.2026 ab.
Der Settings-Stempel protokolliert alle Felder, alte Exporte bleiben zuordenbar.

OFFEN zur Entscheidung, nach Dringlichkeit:
1. Mindesthistorie (drei Monate). Der Waiver holt sonst SpaceX herein.
2. In-Eligible-Filter vor die Segmentierung ziehen, Liste befuellen (enthaelt nur Dummys).
3. Segment auf Firmenebene statt Wertpapierebene.
Davor: Helvetica-Selection zum 19.08.2026 gerechnet, gegen die Live-Segmente aus dem CLOSING-File
verifiziert und als Excel abgelegt (siehe Eintrag 2026-08-29). OFFEN zur Abnahme: die Size-Buffer-Variante (der Live-Index folgt
"Symmetrisch", die App steht per Default auf "Aufstieg am Cut-off") und die Frage, ob
Galderma als 11. Large Cap wirklich ganz aus dem Index fallen soll.
Davor: Kundenrueckfrage zu "Europe Markets Index vs MSCI Europe" beantwortet (siehe Eintrag
2026-08-27), und `..._Fill_Up.xlsx` als Arbeitsmaster auditiert: bestes der vier Files.
OFFEN: linienbezogene MCap-Spalte beim File-Merger anfordern, dann fallen Mehrlinien-Luecken
und FF > Total-Anomalie gemeinsam weg. Davor: Diagnose, warum `..._Complete_ohne_BBG.xlsx`
und `..._incl._FloatMCapCalc.xlsx` verschiedene Ergebnisse liefern (Eintrag 2026-08-26).
Davor: Max-Price-Regel auf ATVR-Bedingung umgestellt und abgenommen (Stand: teurer Ast 10/5 scharf,
normaler Ast 0 wegen der indischen BSE-Datenlage). Davor: Spin-off-Liquiditaets-Ausnahme haengt
am Horizont statt am Seed-Termin. Davor:
Liquiditaets-Buffer war wirkungslos, ist korrigiert und gemessen. Davor: Spin-off-Regel
eingebaut und verifiziert. Davor: UI-Verbesserungen rund um
Reproduzierbarkeit und den Size-Buffer (Punkte 1-4 der Liste vom 2026-08-24). Davor: Abgleich NX-EU-LM (Europe Pooled) gegen MSCI Europe: warum fallen MSCI-Titel bei uns raus, und
welches Buffer-Framework wuerde sie halten. Davor: Europe MP (Pooled) hat denselben
Auswertungs- und Exportblock wie der Multi-Period-Tab bekommen.

## Entscheidungen

- **2026-08-29, ENTSCHEIDUNG Nico: Helvetica faehrt "Aufstieg am Cut-off", und zwar ueber
  den Sidebar-Schalter wie bisher.**
  Segmentgrenzen damit: Aufnahme UND Aufstieg fuer alle an den glatten Schwellen 70 / 85 / 99,
  Verbleib fuer Bestandstitel bis unter 75 / 90 / 99,5. Vorher beschrieb die Guideline
  symmetrische Baender (Mid 65 bis 90, Small 84,5 bis 99,5) und der Live-Index rechnete auch so
  (belegt am 20.05.: symmetrisch trifft 36 von 37 Konstituenten, Aufstieg am Cut-off nur 35).
  Helvetica faehrt jetzt dieselbe Variante wie die NaroIX-Serie.
  **Der Umstellungstermin ist glatt:** zum 19.08. liefern beide Varianten dieselben 37 Titel in
  denselben Sleeves, null Segment-Abweichungen im ganzen Pool, weil kein Titel in einer der
  entscheidenden Zonen liegt (Vorsegment Mid mit Coverage 65 bis 70 %, Vorsegment Small mit
  84,5 bis 85 %). Der Wechsel kostet nichts und wird erst ab dem naechsten Termin wirksam.
  **Kein Sonderweg im Code.** Ich hatte zwischenzeitlich eine Konstante
  `HELVETICA_ENTRY_AT_CUTOFF` eingebaut und den Tab vom Sidebar-Radio entkoppelt; auf Nicos
  Ansage wieder zurueckgebaut. Helvetica nimmt weiterhin, was in der Sidebar steht, und der
  Default dort IST die Guideline-Variante. Die Kriterien-Box zeigt die aktive Variante und
  markiert jede andere Stellung als "nicht die Guideline-Variante".
  **Folge, die man kennen muss:** ein Varianten-Experiment fuer die Serie verstellt Helvetica
  mit. Der Settings-Stempel im Export haelt deshalb fest, womit ein Lauf gerechnet hat.
  Guideline §4 (Tabelle, Erklaertext, Aenderungsvermerk mit Sidebar-Hinweis) und §7
  (Buffer-Zeile + Schalter-Absatz) nachgezogen, Stand auf 2026-08-29.
  **Sechs Assertions** (`test_helvetica_variante_default`): weil Helveticas publizierte
  Methodik jetzt an einem UI-Default haengt, nagelt der Test genau den fest (Options-Reihenfolge
  und `index=0`), dazu beide Tab-Verdrahtungen und eine Verhaltensprobe.
  Mutationsgetestet: `index=1` laesst die Default-Assertion anschlagen. Suite 271 -> 277.
  NB: die Verhaltensprobe war in der ersten Fassung wertlos (Test-Frame erzeugte
  _c_before = 50 % statt 67 %, der Titel war in beiden Varianten Large). Sie prueft die
  Coverage-Annahme jetzt mit, wie es `test_helvetica_entry_at_cutoff` schon tat.

- **2026-08-29, OFFENE METHODIKFRAGE mit 2 Positionen Wirkung: wie weit reicht die
  Coverage-Hysterese?**
  Auf Nicos Ansage wurde die Selection 19.08. noch einmal aus GENAU ZWEI Files gerechnet
  (Screener + CLOSING), ohne das historische Master-File. Erstes Ergebnis: **der Pool ist
  bit-identisch** (112 Titel, Total MCap / Adj_FF_MCap / ADTV / Coverage mit Delta 0). Der
  Screener allein reproduziert das Universe vollstaendig, das alte File steuerte dazu nichts bei.
  Der Unterschied liegt AUSSCHLIESSLICH bei den Vorperioden-Segmenten, und zwar bei Titeln, die
  NICHT im Index sind. Acht Segmente weichen ab, drei davon mit Wirkung:
  EMS-Chemie (87,09 %), Straumann (87,40 %) und Sonova (88,87 %) fallen ohne Vorperioden-Segment
  hart auf Small und landen im Small-Sleeve auf den Raengen 7 / 3 / 4, verdraengen dort also
  Galenica, Barry Callebaut und SIG Group.
  **Zwei Lesarten, beide vertretbar:**
  * *Pool-weit* (so rechnet der Code): `_prev_seg` kommt aus `_full`, also jedem Titel des
    Vorperioden-Pools inkl. Micro. Passt zu MSCI/Solactive, wo Size-Segmente auf dem ganzen
    Markt definiert sind, und zu unseren eigenen Swiss-Size-Sub-Indizes. Braucht Pool-State
    ueber die Perioden, also ein Historien-File. Ergebnis: **3 raus / 3 rein**.
  * *Nur Konstituenten* (so liest sich Guideline §7): "Inkumbenten = die selektierten
    Konstituenten (55 %) der Vorperiode", und die Coverage-Hysterese steht in derselben
    Buffer-Tabelle. Braucht nur das CLOSING-File. Ergebnis: **5 raus / 5 rein**.
  Guideline §4 formuliert es dagegen als "Segment der Vorperiode", was pool-weit klingt. Der
  Text ist also an dieser Stelle nicht eindeutig, und die Frage ist keine Kosmetik: sie
  entscheidet ueber 2 Netto-Positionen und ueber den Turnover (8,1 % gegen 13,5 %).
  **Zur Entscheidung Nico.** Danach Guideline §4/§7 eindeutig machen und ggf. den Code angleichen.
  Exporte: `..._2026-08-19.xlsx` (pool-weit) und `..._2026-08-19_2Files.xlsx` (nur Konstituenten).

- **2026-08-29, Helvetica-Selection 19.08.2026 gerechnet: 3 Abgaenge, 3 Zugaenge.**
  Datenbasis: FactSet-Screener `Swiss-Made Portfolio Index - Selection_19_08_2026.xlsx`
  (268 CH-gelistete Titel, CHF) als 48. Periode an den Helvetica-Master angehaengt, plus
  `CLOSING_DE000A4AV9S7_20260819.xlsx` als Bestand (37 selektierte Konstituenten).
  Ergebnis: **raus** Partners Group (Mid Rang 11, nach den 8 harten Plaetzen nur 2
  Bandplaetze frei), BKW (Small Rang 17, Halteband endet bei 13), Investis (3M-ADTV
  640k unter der Maintenance-Schwelle 750k); **rein** Helvetia Baloise (Mid Rang 7),
  SIG Group (Small Rang 8), Infracore (neuer RE-Titel, Micro, ADTV 1,79 Mio.).
  Turnover 3 von 37. Export: `Helvetic Selection/NaroIX_Helvetica_Selection_2026-08-19.xlsx`
  mit Zusammensetzung, Aenderungen samt Begruendung, CH-Universe und Settings-Stempel.

- **2026-08-29, die Size-Buffer-Variante ist empirisch geklaert: der Live-Index laeuft
  SYMMETRISCH, nicht "Aufstieg am Cut-off".**
  Die Guideline (§4, §7) dokumentiert die symmetrischen Baender 65-90 / 84,5-99,5, die App
  steht per Default auf "Aufstieg am Cut-off". Der Abgleich der nachgerechneten Vorperiode
  20.05.2026 gegen den Live-Index entscheidet das: **symmetrisch trifft 36 von 37**,
  "Aufstieg am Cut-off" nur 35 von 37 (dort fehlen Swisscom und Alcon, dafuer stehen Lindt PS
  und Helvetia Baloise drin). Die Guideline hat also recht und der App-Default weicht ab.
  Auf den 19.08. wirkt die Variante genau eine Position: symmetrisch faellt Partners Group,
  bei "Aufstieg am Cut-off" faellt stattdessen Swisscom (dort ist Swisscom ueber die Kette in
  Large gerutscht und wird als Rang 12 verworfen). Die restlichen 36 sind identisch.
  OFFEN: Sidebar-Default auf Symmetrisch stellen, oder die Guideline auf die andere Variante
  umschreiben. Bis dahin nicht blind mit App-Defaults rechnen.

- **2026-08-29, das CLOSING-File hat jetzt eine Spalte `Segment` (Nico nachgeliefert): die
  Vorperioden-Segmente sind damit belegt statt rekonstruiert.**
  Damit faellt die groesste Unsicherheit des Laufs weg. Abgleich: **36 der 37 Live-Titel
  stimmen Segment fuer Segment mit der nachgerechneten Kette** (Large 10, Mid 10, Small 10,
  RE 7). Insbesondere bestaetigt: **SGS = Mid Cap**, Julius Baer und Logitech = Small Cap,
  VAT / Swisscom / Sandoz / Partners Group = Mid Cap. Das waren genau die Faelle, die aus den
  Index-Gewichten nicht ableitbar sind (Mid und Small haben beide 1,5 %).
  Der Finallauf setzt die 30 Aktien-Segmente aus dem File und laesst nur den restlichen Pool
  aus der Kette kommen; Ergebnis **Titel, Sleeve und True_Segment identisch** zum reinen
  Kettenlauf. Die Selection 19.08. steht damit unveraendert.
  **Merkregel fuer kuenftige Termine:** die Spalte `Segment` im CLOSING-File ist der SLEEVE.
  Solange kein Sleeve Aufruecker enthaelt, ist er gleich dem True_Segment; sobald ein Segment
  unter 10 Titel faellt, ist er es nicht mehr. Und fuer Titel ausserhalb des Index gibt es
  weiterhin keinen externen Beleg.

- **2026-08-29, wie stark der Lauf an den Vorperioden-Segmenten haengt: 13 von 112 Titeln.**
  Vollstaendig ausgezaehlt (je Titel das Segment auf die Alternative gesetzt, Composite neu
  gerechnet): 23 Titel liegen ueberhaupt in einer Hysterese-Zone, bei 13 davon verschiebt ein
  anderes Vorsegment die Selektion. Ohne Vorperioden-Segmente waere das Ergebnis 5 raus / 5 rein
  statt 3/3 (SGS und VAT fielen auf Small, das flutet den Small-Sleeve und draengt Galenica,
  Barry Callebaut, Flughafen und SIG raus).
  Nach dem Abgleich oben sind davon nur noch die **Nicht-Konstituenten** offen, praktisch
  EMS-Chemie (86,65 %), Straumann (86,93 %) und Sonova (89,00 %): waere einer davon am 20.05.
  Small statt Mid gewesen, verdraengte er SIG Group aus dem Small-Sleeve. Fuer die gibt es
  ausserhalb der Kette keine Quelle.

- **2026-08-29, die eine verbleibende Abweichung (Alcon) ist Pfadabhaengigkeit und folgenlos.**
  Im Live-Index ist Alcon am 20.05. Mid Cap, in unserer ab 2014 kalt geseedeten Kette Large Cap
  (Coverage 74,17 %, Halteband bis 75). Als Large landet Alcon auf Rang 11 und faellt ganz raus,
  weil der Ueberschuss nicht nach unten weitergegeben wird; deshalb steht in der Rekonstruktion
  Helvetia Baloise statt Alcon. Gegenprobe gerechnet (Vorperioden-Segment von Alcon auf Mid
  gesetzt): der 19.08. ist **Titel fuer Titel und Sleeve fuer Sleeve identisch**. Fuer den
  neuen Termin wurden ausserdem bewusst die ECHTEN Live-Konstituenten als Inkumbenten
  verwendet, nicht die Rekonstruktion. Gleiches Muster wie [[cboe-smallcap-lockin]].

- **2026-08-29, Nebenbefund: Galderma faellt als 11. Large Cap komplett aus dem Index.**
  Coverage 67,98 %, also klar Large (Cut 70), aber nach Float nur Rang 11 im Segment. Die
  Guideline verwirft den Ueberschuss eines Segments ausdruecklich, statt ihn nach unten
  durchzureichen ("Kein Uebertrag nach unten"), also ist der groesste nicht enthaltene
  Schweizer Titel mit 33 Mrd Float-MCap draussen, waehrend Mid-Titel mit 15 Mrd drin sind.
  Regelkonform, aber erklaerungsbeduerftig. Betrifft auch schon den Live-Index (Galderma ist
  dort ebenfalls nicht enthalten), ist also keine Aenderung, sondern ein Strukturthema.
  Zur Entscheidung: so lassen, oder den Ueberschuss ins naechstkleinere Sleeve abstufen.

- **2026-08-28, doppelte Captions im Helvetica-MP-Tab entfernt.**
  Mit der Kriterien-Box waren zwei der drei Hinweiszeilen redundant (Bestandsschutz-Zustand,
  ADTV/Coverage/FF-Schwellen) und die dritte zur Haelfte. Geblieben sind nur die Aussagen,
  die aus der Box NICHT ableitbar sind: die Kaskaden-Warnung (ein Aufsteiger nach Large kann
  bei Rang > 10 ganz aus dem Index fallen, weil der Ueberschuss nicht nach unten
  zurueckgegeben wird) und eine st.warning, wenn der Bestandsschutz teilweise abgeschaltet
  ist. Faustregel dabei: Werte gehoeren in die Box, Verhaltenswarnungen in den Flowtext.

- **2026-08-28, Kriterien-Box in allen drei MP-Tabs, Perioden-Range bei Helvetica.**
  `_criteria_box(variant)` rendert die "Selektionskriterien"-Infobox aus den AKTIVEN
  Sidebar-Werten (nicht aus SETTINGS_NOW: die Box zeigt, womit der naechste Lauf rechnen
  WUERDE; was ein gelaufener Lauf benutzt hat, steht im Settings-Blatt des Exports).
  Zwei Auspraegungen: `serie` fuer Multi-Period und Europe MP (EUMSS, ATVR-Screen, Buffer,
  MSCI Logic, Size Integrity, Capping), `helvetica` fuer die eigene Pipeline (kein EUMSS,
  kein ATVR-Screen, dafuer Rang-Band, Sleeve-Gewichte und die CHF-ADTV-Schwellen).
  Steht in allen drei Tabs direkt ueber dem Start-Button.
  Helvetica bekommt zusaetzlich den **Start-/End-Perioden-Picker** wie die anderen beiden
  Tabs: die Termine kommen weiter aus dem File, gewaehlt wird nur der Ausschnitt
  (`_reb_all` -> `_reb`). Keine Frequenz- oder Jahresauswahl — die war am 2026-08-28
  bewusst entfallen, weil der Turnus Guideline-Sache ist.
  Dezimaltrenner in der Box auf deutsches Komma vereinheitlicht (7,5 % statt 7.5 %).


- **2026-08-28, Helvetica-Testabdeckung geschlossen: 231 -> 251 Assertions.**
  Vier neue Tests fuer genau die Regeln, die heute geaendert wurden und bis dahin KEINEN Test
  hatten: `test_helvetica_adtv_maintenance` (Entry gegen Maintenance je Titel, plus der Fall
  unter beiden Schwellen), `test_helvetica_high_price_rule` (ATVR-Bedingung greift, faellt,
  Maintenance-Rabatt, und der Aus-Fall ohne ATVR-Modus), `test_helvetica_ineligible`
  (Entfernung nach der Segmentierung, auch in der Komposition), `test_helvetica_dedup_most_liquid`
  (liquideste Linie gewinnt, fehlende Entity ID kollabiert NICHT).
  Nicht noetig waren Tests fuer Spin-off-Entity-ID-Keying und das Rang-Band — die decken
  `test_spinoff_other_key_fn` und `test_rank_band_buffer` bereits ab.
  **Mutationsgetestet:** drei Regressionen kuenstlich eingebaut (ADTV-Maintenance entfernt,
  Micro aus dem Kaskaden-Pool genommen, Dedup abgeschaltet) — 7 Assertions schlagen an. Die
  Tests schuetzen also wirklich, statt nur gruen zu sein. Datei danach aus dem Backup
  wiederhergestellt und wieder 251/251.


- **2026-08-28, Helvetica-File geprueft: in Ordnung. Frueherer "massive Float-Luecken"-Alarm war falsch.**
  `Old Files/NaroIX_Helvetica_Selection_Master_Final_05_2026_OFFICIAL.xlsx`, 293 Zeilen x 448
  Spalten, ein Blatt "Master", 47 Perioden 2014-11-19..2026-05-20, alle Werte in CHF.
  **Selection Dates:** alle 47 Termine stehen in `Selection Dates.xlsx`. Das Validierungs-Gate in
  `load_master_excel` (Zeile ~1009, verwirft Termine die nicht in der Liste stehen) feuert hier
  also nie — die Termine kommen faktisch aus dem File, wie es der Tab jetzt auch macht. Das Gate
  bleibt ein theoretisches Risiko fuer den Tag, an dem ein File einen neuen Stichtag mitbringt.
  In der Liste, aber in keinem File: **2015-01-01** — Artefakt, laut Nico ignorierbar. Fuer die
  Laeufe harmlos (kein Master hat eine Spalte dafuer; der Sidebar-Fallback faengt es ab).
  **Float-Alarm relativiert:** die "81 von 293 Zeilen ohne Float" waren fast alle Panel-Auffuellung.
  73 davon haben in KEINER Periode einen Kurs, sind also Wertpapiere die im Zeitraum nie gehandelt
  haben. Nur 8 Zeilen haben Kurs ohne Float, davon eine nennenswert (LafargeHolcim als Zweitlinie;
  die Primaerlinie Holcim hat in allen 47 Perioden Float) und sieben Kleinstwerte, die am
  ADTV-Screen ohnehin scheitern. Sauber gerechnet: **211 von 219 jemals handelnden Zeilen haben
  Float.** Das File ist in Ordnung.
  **Was bleibt (ein Einzelfall, kein Datenproblem):** Lindt PS (LISP) hat Float in nur 13 von 47
  Perioden, die Namenaktie (LISN) in allen 47. Weil LISN in allen 47 Perioden ueber CHF 20.000
  notiert, faellt sie unter der alten Preisregel raus — in den 34 Perioden ohne LISP-Float ist
  Lindt damit gar nicht im Universe. Das erklaert, warum die neue Preisregel 27 Perioden bewegt
  (nicht die frueher genannten 7, die waren auf dem USD-Master gemessen).

- **2026-08-28, Micro-Fill-up geschlossen — letzte Guideline-Luecke der Kaskade.**
  Der Kaskaden-Quellpool im Composite kam aus `helv` (nur L/M/S), Micro war damit unerreichbar
  und der Eintrag `"Micro Cap": 3` in `_SEG_RANK` toter Code. Eine Zeile geaendert:
  `helv_eq` speist sich jetzt aus `helv_full_pool`. Micro bildet weiterhin KEIN eigenes Sleeve
  (die Schleife laeuft nur ueber HELVETICA_EQUITY_SLEEVES) und wird korrekt als "Aufruecker"
  mit True_Segment "Micro Cap" gefuehrt.
  **Wirkung ueber 47 Perioden: exakt null** (0 Perioden mit Unterschied, 0 Titel). Grund:
  Small hat im CH-Universe min 40 / median 53 eigene Titel, kommt also nie in die Naehe der
  Zehnergrenze. Deshalb ist der Pfad historisch nie gelaufen — und deshalb war der Defekt
  auch nie aufgefallen.
  **Sieben neue Tests** (`test_helvetica_micro_fillup`), die den Pfad zum ersten Mal ueberhaupt
  ausfuehren: synthetischer CH-Frame mit Small-Cut bei 90 % statt 99 %, sonst faellt Small
  strukturell nie unter 10. Inklusive Gegenprobe (ohne Micro im Pool bleibt das Sleeve LEER,
  die 15 % verfallen) — das war der Zustand vor dem Fix. Suite jetzt 238 Tests.
  Nebeneffekt dokumentiert: der Fallback nimmt `_srank > _sr`, also ALLE kleineren Segmente,
  nicht nur das naechstkleinere. Praktisch inert (nach Float sortiert, Mid/Small nie erschoepft),
  aber in Docstring und Guideline jetzt korrekt beschrieben.

- **2026-08-28, Helvetica-MP hat KEINE eigenen Methodik-Bedienelemente mehr.**
  Der Tab-Toggle "Maintenance Buffer" ist raus; der Bestandsschutz kommt jetzt aus den beiden
  Sidebar-Schaltern, und zwar getrennt statt zusammengefasst:
  `apply_buffer` -> Maintenance-Schwellen (FF, ADTV) + Rang-Band 8/13 der Sleeves
  (`incumbents_isin`), `apply_size_buffer` -> Coverage-Hysterese der Segmente
  (`prior_segments`). Das ist feiner als der alte eine Toggle und deckt sich mit Multi-Period
  und Europe MP, wo dieselben zwei Schalter dieselben zwei Schichten treffen. Auch
  `m_max_price_atvr` haengt jetzt an `apply_buffer` statt am Tab-Toggle.
  Statt des Schalters zeigt eine Caption den Zustand beider Sidebar-Schalter und warnt, wenn
  einer aus ist ("nicht guideline-konform, dient dem Vergleich").
  **Im Tab ist damit genau ein Bedienelement uebrig: die Termin-Auswahl der Detailansicht.**
  Alles andere kommt aus dem File (Termine) oder der Sidebar (Schwellen, Buffer, Variante,
  Universe-Filter). Konfig-Signatur entsprechend erweitert.

- **2026-08-28, Helvetica-MP Terminsteuerung entfernt — Termine kommen aus dem File.**
  Frequenz-Preset (Quartalsweise/Halbjaehrlich/Jaehrlich/Eigene Monate) und die beiden
  Jahres-Selectboxen sind raus. `_reb = sorted(master_data["detected_dates"])`, fertig.
  Begruendung: die Guideline legt den Turnus fest (quartalsweise), er ist keine
  Bedienentscheidung; und die Presets hatten stille Kanten — "Jaehrlich" nahm die hoechste
  MONATSNUMMER (also Nov, nie den aktuellen Aug-Termin), "Halbjaehrlich" war auf Mai+Nov
  verdrahtet und fiel bei anderen Monaten kommentarlos auf ALLE zurueck. Wer einen kuerzeren
  Lauf braucht, laedt ein kuerzeres File.
  Der **Maintenance Buffer** bleibt, aber umetikettiert als "aus = Vergleichslauf ohne
  Bestandsschutz" mit dem Hinweis, dass Aus nicht guideline-konform ist. Im Tab sind damit nur
  noch zwei Bedienelemente: dieser Toggle und die Termin-Auswahl der Detailansicht.
  Kaskaden- und Schwellen-Captions leiten ihre Zahlen jetzt aus `_helv_rules` ab statt sie hart
  zu schreiben — sonst haetten sie 70/85 gezeigt, waehrend der Lauf gegen Sidebar-Werte rechnet.
  Verifiziert: das CHF-File ergibt weiter 47 Termine (2014-11-19..2026-05-20), identisch zum
  frueheren Default "Quartalsweise (alle)" ueber alle Jahre.

- **2026-08-28, Helvetica-Schwellen kommen jetzt aus der SIDEBAR (Entscheidung Nico).**
  Begruendung: die Guideline ist noch nicht final (ETF nicht live), Anpassungen sollen ohne
  Code-Aenderung durchrechenbar sein, und die Reproduzierbarkeit haengt am Settings-Stempel.
  **Voraussetzung war eine Luecke:** `SETTINGS_NOW` wurde nur fuer `multi_settings` und
  `eupool_settings` gespeichert — die Helvetica-Exporte hatten KEIN Settings-Blatt. Ist ergaenzt
  (`helv_mp_settings` + Blatt "Settings" im Termin-Detail- und im Multi-Period-Export).
  Verdrahtet ueber ein `rules`-Dict (`_helv_rules_from_sidebar()`): Coverage-Cuts aus
  large/mid/small_thr, Min FF aus min_ff_pct/buffer_min_ff, Haltebaender als Cut + size_buffer_pp
  (Mid/Small folgt size_buffer_pp_ms, falls gesetzt) + small_buffer_pp, ADTV aus
  new_adtv_dm/buffer_adtv_dm. `HELVETICA_RULES` bleibt als Fallback fuer Tests und Headless.
  Konfig-Signatur des MP-Tabs um die Schwellen erweitert, sonst zeigt er Ergebnisse zu alten Werten.
  **Verifiziert: bei Sidebar-Defaults exakt identisches Ergebnis** (Pool 113, L+M+S 88,
  37 selektiert, Selektionsmenge deckungsgleich) — die Kopplung ist verhaltensneutral.
  NB: mit dem Live-Gang sollte die Kopplung wieder geloest werden, sonst verstellt ein
  Serien-Experiment die publizierte Methodik.

- **2026-08-28, Helvetica-ADTV-Umschalter im Tab entfernt (war ein Testhebel).**
  Die Auswahl $0,25M / $0,5M / $1,0M war ein Testhebel aus der Entwicklungsphase (Nico bestaetigt),
  kein Guideline-Parameter. Neu `HELVETICA_ADTV_ENTRY = 1_000_000`, Maintenance ueber
  `HELVETICA_ADTV_MAINT_RATIO = 0.75`. Beide Bedienelemente entfernt (Radio im Single-Tab,
  Selectbox im MP-Tab), `adtv_thr=None` in beiden Funktionen faellt auf die Konstante zurueck.
  Der Wert stand ohnehin auf beiden Tabs per Default auf $1,0M, es aendert sich also nichts an
  den Ergebnissen. Bewusst NICHT an die Sidebar-Felder (DM ADTV / ADTV DM Maint.) gehaengt:
  Helvetica ist ein publiziertes Produkt mit eigener Guideline, seine Schwellen sind Konstanten
  wie 70/85/99 und 10 / 7,5 %.

- **2026-08-28, Helvetica bekommt Spin-off-Aufnahme und In-Eligible-Filter.**
  Beide liefen bisher nur in der Serie. Neu in `build_helvetica_pipeline` und
  `build_swiss_size_subindices`: `ineligible_df` / `apply_ineligible` / `selection_date`
  (angewendet NACH der Segmentierung, wie in run_selection_pipeline) und `adtv_exempt_isin`
  (Spin-off-Liquiditaets-Ausnahme, greift nur wenn der 3M-Wert fehlt oder 0 ist).
  Das Seeding laeuft ueber die **Entity ID**, weil dort die Vorperioden-Segmente liegen;
  `seed_spinoff_incumbents` hatte den `key_fn`-Hook dafuer schon vorgesehen. Die geseedeten
  Entity IDs werden fuer Maintenance-Schwellen und Rang-Band auf ISIN zurueckgespiegelt, dazu
  ein zweiter State `_prev_ent` (Entity IDs der selektierten Konstituenten).
  **Wirkung ueber 48 Perioden: null.** Alle 48 Perioden identisch, Turnover unveraendert
  (70 Abgaenge / 74 Zugaenge). Protokoll: Italgas (Mutter Snam, Mailand) und Magnum (Mutter
  Unilever, Amsterdam) korrekt verworfen, weil die Muetter nie Helvetica-Konstituenten waren.
  **Sandoz** (aus Novartis, 2023-11-15) wird korrekt geseedet und erbt Large Cap, landet ueber
  die Coverage-Hysterese aber in Small Cap (das Band haelt nur bis 75 %) - genau das
  selbstbegrenzende Verhalten, das die Spin-off-Regel beschreibt. Sandoz bestand die
  Entry-Schwellen ohnehin, u.a. weil FactSet das 3M-ADTV bei jungen Titeln auffuellt
  (siehe [[factset-adtv-padding]]), die Liquiditaets-Ausnahme also gar nicht greifen musste.
  In-Eligible ist derzeit ein Leerlauf: die Liste enthaelt nur 2 Beispielregeln (CN/IN), keinen
  Schweizer Titel. Beides ist damit Absicherung fuer die Zukunft, keine Backtest-Aenderung.

- **2026-08-28, Helvetica nutzt die Hochpreis-Regel aus der Sidebar (ATVR-Bedingung statt hartem Cut).**
  Bisher reichte Helvetica `max_closing_price` direkt an `build_new_universe` und schnitt hart bei
  20.000; die ATVR-Bedingung der Serie (min(ATVR 3M, 6M) >= 10 % neu / 5 % Bestand) erreichte den
  Tab nie. Neu: `_helv_high_price_ok()` als gemeinsamer Helfer, Parameter `max_price` /
  `max_price_atvr` / `m_max_price_atvr` in `build_helvetica_pipeline` und
  `build_swiss_size_subindices`, Aufrufer uebergeben im ATVR-Modus `None` an `build_new_universe`.
  Betroffen ist in der Schweiz ueber alle 48 Perioden **ausschliesslich LISN** (Lindt Namenaktie,
  Kurs ~117k, ATVR 17 bis 56 %, besteht immer).
  **Wirkung A/B ueber 48 Perioden:** Helvetica-Index 47 von 48 Perioden identisch. Einzige
  Abweichung 2016-08-17, dort fuehrt der Dedup Lindt ueber LISN statt LISP (LISN dort 1,010x
  liquider), gleiches Sleeve Mid Cap, gleiches Gewicht 1,50 %. Turnover +1 Abgang / +1 Zugang in
  12 Jahren, kein Whipsaw (Lindt verlaesst den Index 2016-11 in beiden Laeufen ohnehin).
  Helvetica-Pool in allen 48 Perioden identisch, weil der Dedup so oder so eine Linie behaelt.
  **Die eigentliche Wirkung liegt in den Swiss-Size-Sub-Indizes** (Variante B, alle Share Lines):
  LISN kommt in ALLEN 48 Perioden dazu (+48 Titel, 44 Mid Cap / 4 Small Cap), Lindts Gewicht im
  Mid-Cap-Sub-Index am 2026-08-19 steigt 3,82 % -> 7,77 %. Das korrigiert eine echte Untererfassung:
  LISN traegt 52 bis 56 % von Lindts Float, und Variante B sieht ausdruecklich alle Linien vor.
  **Nebenwirkung, gewollt:** `_gm_u_global` schneidet im ATVR-Modus nicht mehr hart, damit ist der
  Bug behoben, dass GIMI/Europe-Single ueber `prebuilt_universe` am harten Cut haengen blieben,
  obwohl `run_selection_pipeline` an dieser Stelle `None` uebergibt. Gemessen 2026-08-19:
  Universe +3 Zeilen, NX-EU-LM 363 -> 364 (Lindt Namenaktie rein, kein Abgang), NX-GM-LM bleibt
  2500 und tauscht (Lindt + Berkshire A rein, Alnylam + Martin Marietta raus, Coverage-Treppe
  rueckt nach), NX-GM-AC 7941 -> 7940. GIMI/Europe rechnen damit wie der Multi-Period-Tab.
  Guideline-Draft §6, Schritt 3b und Schicht 1 nachgezogen. Regressionstests 231/231 gruen.

- **2026-08-28, Helvetica bekommt einen ADTV-Maintenance-Buffer (Entry 1,0 Mio / Bestand 750k).**
  Die Liquiditaet war Helveticas einzige Schwelle OHNE Bestandsschutz, obwohl FF % (10 / 7,5) und
  Coverage (70/85/99 gegen 75/90/99,5) laengst einen hatten. Neu: `HELVETICA_ADTV_MAINT_RATIO = 0.75`,
  Parameter `adtv_maint_thr` in `build_helvetica_pipeline` und `build_swiss_size_subindices`
  (None = adtv_thr x 0,75). Wirkt pro LINIE: die Schwestergattung eines Bestandstitels bleibt
  Neukandidat. Inkumbenten sind wie gehabt die selektierten Konstituenten der Vorperiode.
  **Wirkung ueber alle 48 Perioden gemessen (A/B, App-Defaults, Entry $1,0M):** 42 Perioden
  identisch, 6 Perioden je genau 1 Titel Unterschied, **alle 6 in Real Estate**, Equity in KEINER
  Periode veraendert. Turnover 71 -> 69 Abgaenge, 74 -> 73 Zugaenge. Max. aktive Abweichung
  3,00 pp (2021-02-17), selektiertes Gesamtgewicht konstant 55 %. Grund fuer die Asymmetrie:
  die Equity-Sleeves sind fixe Top-10 nach Float, ein liquiditaets-marginaler Titel ist auch
  float-klein und liegt ohnehin jenseits Rang 10; Real Estate nimmt dagegen ALLE qualifizierten
  Titel inkl. Micro, also schlaegt dort jeder gehaltene Titel voll durch. Faelle: Intershop
  (2021-02, 873k), Peach Property (2022-02/05/08, 908k/857k/802k), HIAG (2026-02, 973k),
  Investis (2026-08, 797k) - alle echte Inkumbenten im Band 750k bis 1,0M.
  Guideline-Draft Schritt 3 und §7 nachgezogen. Regressionstests 231/231 gruen.
  OFFEN zur Abnahme: ist 0,75 das gewuenschte Verhaeltnis, und soll der Buffer wirklich auch fuer
  Real Estate gelten (dort liegt die gesamte Wirkung).

- **2026-08-27, `..._Fill_Up.xlsx` ist der Arbeitsmaster und das beste der vier Files.**
  Kundenlauf exakt reproduziert: Variante 1 = 375 Titel / 343 MSCI-Treffer, Variante 2 = 403 / 365,
  ISIN fuer ISIN identisch zum verschickten File (Mid/Small-Kante 5 bzw. 7 pp, sonst App-Defaults).
  Konstruktion: Roh-Float von ohne_BBG unveraendert (1.374.288 Zellen, nur 5 geaendert: ABN AMRO 2x,
  FinecoBank 2x, BAWAG 1x) plus 199.831 von 670.320 Luecken gefuellt mit `Share MCap x FF%`,
  aber **nur bei einlinigen Firmen** (mehrlinig gefuellt: 0). Deshalb kein Phantom-Float:
  EU-Firmen mit unmoeglicher Float-Summe bleiben bei 8 / 29 Mrd wie in ohne_BBG, FloatMCapCalc
  hat 71 / 902 Mrd. Gefuellte Werte alle mit Float/Share <= 1,000. EU-Float-Aggregat steigt nur
  0,1 bis 1,7 % je Periode (FloatMCapCalc: 8 bis 25 %), die Coverage-Treppe wird also nicht verzerrt.
  MSCI-Europe-Overlap der vier Files bei ms=7 pp: Fill_Up 365 von 396 (98,20 % Gewicht),
  Complete 363, ohne_BBG 362, FloatMCapCalc 359. Fill_Up holt die genannten Luecken zurueck
  (BASF, Brenntag, Merck KGaA, Linde, Lufthansa, Bayer, Vonovia, Porsche SE Vorzug, Delivery Hero,
  Pandora, ICG, Dino Polska).
  Restschwaechen: FF > Total unangetastet (1.377 Zeilen, in DM-Europa nur 112 Zeilen / 0,21 % des
  Floats, max Infineon 1,10x); 1.591 handelnde Mehrlinien-Zeilen weiter ohne Float (BMW Vorzug,
  Grifols Pref B, Telecom Italia Rsp, FUCHS Vorzug, RWE Vorzug); global 5.824 handelnde einlinige
  Zeilen offen, v.a. China (Zhongji Innolight 156 Mrd, Yushu 51 Mrd), dort fehlt auch das
  FF%-Feld; in DM-Europa nur 12 Zeilen > 1 Mrd offen, davon relevant nur INNIO (18,9 Mrd, FF% 0,0);
  118 Zeilen gefuellt, obwohl die Gattung am Stichtag nicht handelt (scheitern am ADTV-Screen,
  wuerden nur bei "Labeling vor Liquiditaet" in den Coverage-Nenner rutschen).

- **2026-08-27, Kundenrueckfrage zu den Marktkapitalisierungen war ein Lesefehler in SEINER Spalte.**
  Die zitierten Werte (Novo B "123 Mrd", P911 "4,5 Mrd") stehen im Blatt "MSCI Europe", Spalte
  `Marktwert`. Die Spalte ist der **Positionswert des ETF in EUR**: Summe = 12,1126 Mrd EUR
  (Fondsvolumen), und `Marktwert / Summe` reproduziert die Spalte "Gewichtung (%)" auf 0,02 pp.
  Novo steht dort mit 123,6 **Mio**, P911 mit 4,56 Mio. Unsere Varianten-Blaetter enthalten
  ueberhaupt keine Marktkapitalisierung, nur `Index_Weight`. Der zweite Teil seiner Beobachtung
  ist inhaltlich richtig: gewichtet wird nach Free Float. Novo 178 Mrd EUR Total gegen 128 Mrd
  Free Float (Novo Holdings 28 %), Porsche AG 40 Mrd gegen 4,6 Mrd (nur Vorzuege gelistet, VW
  haelt 75 % der Staemme) - daher auch bei MSCI nur 0,04 % Gewicht.

- **2026-08-27, Rexel/Indra/Hensoldt draussen, Elisa/Kingfisher drin ist die Hysterese, kein Fehler.**
  Coverage-Positionen am 2026-08-19 (Fill_Up, ms=7 pp): Indra 85,90 %, Hensoldt 86,32 %,
  Rexel 86,67 % (alle Vorsegment Small Cap) gegen Kingfisher 91,13 % und Elisa 91,62 %
  (beide Vorsegment Mid Cap). Die drei stehen in der Coverage-Rangfolge also VOR den beiden;
  die Inversion existiert nur, wenn man an der Total-Marktkapitalisierung misst. Die 92er-Kante
  ist eine Halte-, keine Aufnahmegrenze: Aufsteiger brauchen die glatte 85 %.
  Gemessen im Band 85 bis 92: **182 Titel, 88 Bestandstitel alle drin, 94 Aufsteiger alle draussen**;
  kleinster gehaltener 7,0 Mrd (Elisa), groesster abgewiesener 13,2 Mrd (Delivery Hero).
  Die 31 fehlenden MSCI-Titel: 19 Hysterese (0,68 % Gewicht), 7 knapp jenseits 92 (alle zwischen
  92,11 und 92,49 %, 0,21 %), **4 Country Mapping** (Sunbelt Rentals ex-Ashtead 0,22 %, AerCap,
  Millicom je Country of Risk = USA; CSG N.V. Country of Risk = Tschechien, also EM; zusammen
  0,47 %), 1 ISIN nicht im Master (Octave Intelligence SDR). Summe 1,46 % MSCI-Gewicht.
  Die vier Country-Mapping-Faelle sind der einzige Punkt, der nicht "Regel wirkt wie vorgesehen"
  ist, siehe [[factset-country-mapping-rule]].

- **2026-08-26, ohne_BBG vs incl._FloatMCapCalc: der Unterschied ist AUSSCHLIESSLICH die
  Float-Spalte, und beide Varianten sind kaputt, nur unterschiedlich.**
  Zellweiser Abgleich beider Files (59.545 Zeilen x 458 Spalten, auf Perm ID + ISIN + Symbol +
  Exchange Ticker ausgerichtet): **identische Zeilenmenge** (Setdifferenz 0 in beide
  Richtungen), aber 13.896 Zeilen (23 %) in ANDERER Reihenfolge. Abweichend sind genau
  **95 von 458 Spalten**: `Float MCap` in allen 48 Perioden und `Float PCT` in 47.
  Closing Price, Total MCap, Share MCap, alle vier ADTV-Horizonte und alle 26 statischen
  Spalten sind bit-identisch. Die Reihenfolge ist irrelevant: im EU-Pool gibt es nur 10 bis 13
  echte Sortier-Ties (Total MCap UND Float identisch, alle aus den 14 bekannten
  Doppel-Primary-ISINs).
  Drei Unterschiede in der Float-Spalte:
  1. **Formel.** FloatMCapCalc = `Share MCap x Float PCT / 100` (38.152 von 38.321 Zeilen
     treffen auf < 0,1 %). ohne_BBG ist FactSets Roh-Float und trifft KEINE der beiden Formeln
     (445 von 29.831 gegen Share x FF%, 414 gegen Total x FF%).
  2. **Datenluecken in ohne_BBG.** FloatMCapCalc hat global 8.468 Zeilen mehr mit Float > 0,
     in DM-Europa 950 (waechst von 0 in 2014 auf 953 in 2026). Die Pipeline filtert
     `FF MCap > 0`, diese Titel fehlen im ohne_BBG-Lauf also komplett. Betroffen sind echte
     Large Caps: BASF in 24 Perioden ohne Float, Brenntag 22, Merck KGaA 19, Linde 15,
     Lufthansa 12, Bayer 10; insgesamt 42 EU-Titel > 5 Mrd in 429 Titel-Perioden.
  3. **Doppelzaehlung in FloatMCapCalc.** `Share MCap` ist ein FIRMEN-Wert: bei 1.800 von 1.806
     Mehrlinien-Firmen tragen alle Linien denselben Share MCap. `Share x Linien-FF%` gibt damit
     JEDER Linie den Float der ganzen Firma. Beispiele 2026-08-19: Roche Namenaktie 13,1 -> 102,9
     Mrd (Primary hat zusaetzlich 371,6), SEB Class C 0,5 -> 38,1 (Primary 35,2), Atlas Copco B
     27,6 -> 96,0 (A-Linie 75,3), BMW Vorzug fehlend -> 40,6 (Stammaktie 22,3), Grifols Pref B
     0 -> 7,2 = 100 % der Firma. In DM-Europa: 113 Nebenlinien, Float 0,175 -> 1,112 Bio USD
     (+536 %), das sind 60 % des gesamten EU-Float-Zuwachses. 71 europaeische Firmen haben in
     FloatMCapCalc eine Float-SUMME ueber ihrer eigenen Marktkapitalisierung (902 Mrd unmoegliche
     Float-Masse), in ohne_BBG sind es 8 Firmen / 29 Mrd. Umgekehrt hat ohne_BBG die bekannte
     FF > Total-Anomalie: 1.372 Zeilen am 2026-08-19, FloatMCapCalc nur 14.
     Passt zu [[freefloat-ff100-anomaly]]: `Share MCap` erklaert die >100 % nicht, und als
     Float-Basis taugt er nur bei Firmen mit EINER gelisteten Linie.
  **Wirkung auf NX-EU-LM** (Europe Pooled, 48 Perioden, App-Defaults, Mid/Small-Kante 7 pp):
  Durchschnitt 403,9 (ohne_BBG) gegen 397,8 (FloatMCapCalc), also -6,1 Titel; **keine einzige
  der 48 Perioden ist identisch**, Delta -1 bis -16; 478 Titel-Perioden nur in ohne_BBG
  (119 verschiedene Titel), 187 nur in FloatMCapCalc (25 Titel). Investierbares Universum
  8.601 -> 9.589 am letzten Stichtag.
  Die Abgaenge liegen zu 357 von 478 im Coverage-Band 85 bis 92, also genau in der Hysterese,
  die die 7-pp-Kante aufspannt. Mechanik: der Zusatz-Float sitzt in Zeilen mit HOHEM Total
  MCap (Nebenlinien werden mit dem Firmen-Total sortiert), die Coverage-Treppe wird kopflastig,
  und Mid Caps rutschen ueber die 92 %-Kante.
  Die 7-pp-Kante ist Verstaerker, nicht Ursache: mit 5 pp bleiben 551 Abweichungen (statt 665)
  und -5,0 Titel (statt -6,1), ebenfalls in 48 von 48 Perioden.
  Reproduzierbar mit `run_eupool.py <master.xlsx> <out_prefix> [ms_pp]` (Streamlit-freier
  Nachbau des Tabs "Europe MP (Pooled)" mit App-Defaults, rund 3 Minuten je File).
  **OFFEN, Entscheidung Nico:** korrekt waere Float = Marktkapitalisierung DER LINIE x FF%
  der Linie. Dafuer fehlt eine linienbezogene Share-MCap-Spalte; `Share MCap` ist
  firmenbezogen. Solange die fehlt, ist keins der beiden Files als Float-Quelle sauber.

- **2026-08-25, BUG: der ADTV-/ATVR-Maintenance-Buffer war komplett wirkungslos, behoben.**
  `apply_liquidity_new` pruefte Bestandstitel auf die reine ISIN (`_norm_isin`), waehrend die
  Run-Schleifen `incumbents_isin` aus `_match_key` fuellen (Perm ID mit ISIN-Fallback) und alle
  anderen Screens derselben Pipeline ebenfalls `_match_key` nutzen. Perm ID ist im aktuellen
  Master in 28.580 von 28.580 Zeilen gefuellt, der ISIN-Fallback greift also nie: gemessen
  **0 von 28.580 Zeilen** bekamen die Maintenance-Schwelle. Jeder Bestandstitel lief jede
  Periode gegen die Entry-Schwelle von 1 Mio, obwohl die Guideline 750k dokumentiert.
  Fix: `_norm_isin` -> `_match_key`, plus vier Regressionstests, die den Key festnageln
  (Incumbent per Perm ID erkannt, Neuzugang scheitert weiter an Entry, ohne Buffer fallen
  beide, ISIN-Fallback funktioniert wenn keine Perm-ID-Spalte da ist).
  **Gemessene Wirkung** (Europe Pooled, 48 Perioden, asym 5 pp, mit Spin-off-Liste):

  | Produkt | alt | neu | Delta | Perioden mit Unterschied | Turnover alt | neu |
  |---|---|---|---|---|---|---|
  | NX-EU-LM | 371 | 373 | +2 | 45/48 | 3,90 % | 3,82 % |
  | NX-DM-LM | 1.440 | 1.443 | +3 | 47/48 | 3,90 % | 3,84 % |
  | NX-GM-LM | 2.800 | 2.823 | +23 | 47/48 | 6,48 % | 6,19 % |

  Der Turnover sinkt in allen drei Produkten, das ist genau die Funktion eines
  Maintenance-Buffers und ein gutes Plausibilitaetssignal. Die 18 neu gehaltenen Titel sind
  Bestandstitel im ADTV-Band 750k bis 1 Mio (Rightmove, Schroders, Waertsilae, Acciona,
  B&M, Alstom u.a.). Keiner davon ist ein MSCI-Only-Titel, der Fix schliesst die MSCI-Luecke
  also NICHT, er repariert nur die dokumentierte Regel.
  Backtests vor dem 2026-08-25 sind mit dem korrigierten Code nicht reproduzierbar.

- **2026-08-25, Banorte-Datenfehler datiert: ab 2024-11-20, die letzten 8 von 48 Perioden.**
  Bis 2024-08-21 ist alles plausibel (FF MCap / Total MCap zwischen 0,86 und 1,09, ATVR 38 bis
  85 %). Von 2024-08-21 auf 2024-11-20 springt die FF MCap von 21,6 Mrd auf 879,4 Mrd bei einer
  Total MCap von 19,7 Mrd, Verhaeltnis 44,55, und das FF-Prozent-Feld wechselt gleichzeitig von
  100,0 auf 87,7. Bleibt kaputt bis 2026-08-19 (Verhaeltnis 46,67, ATVR 1,09 %).
  Also ein AKTUELLES Problem, kein historisches: eine Float-Korrektur muesste nur die letzten
  8 Perioden abdecken, und die 19 mexikanischen Titel, die dadurch nach Small gedrueckt werden,
  fehlen nur dort. Passt zu [[freefloat-ff100-anomaly]].
  Zweite, aeltere Luecke im selben Titel: in 13 Perioden (2016-11 bis 2020-11, plus 2022-08 und
  2022-11) hat Banorte GAR KEINE FF MCap und faellt ueber die `FF MCap > 0`-Exclusion raus.

- **2026-08-25, Guideline-Parametertabelle war an drei Stellen stale, korrigiert.**
  Entry-ADTV stand als DM $2,000,000 / EM $1,000,000 drin, der Code nutzt **1 Mio fuer beide**
  ohne DM/EM-Split. Maintenance-ADTV stand als DM $1.0M / EM $0.5M, korrekt sind **750k fuer
  beide** (von Nico am 2026-08-25 bestaetigt). Und die Max-Price-Zeile beschrieb noch einen
  Step-1-Ausschluss, jetzt Step 6 mit der ATVR-Bedingung 10 % / 5 %.
  Richtig war die Guideline dagegen bei **Min Free Float 10 %** — MEIN Fehler: ich hatte 15 %
  angenommen, weil `min_ff_pct = 0.15` im Code steht, das ist aber nur der Parse-Fallback, das
  Widget-Default ist "10".

- **2026-08-25, WICHTIG: meine Messlaeufe wichen in ZWEI Parametern von den App-Defaults ab.**
  `min_ff_pct` 0,15 statt 0,10 (also strenger) in allen Laeufen, und `max_price` None statt
  20000 in den frueheren Laeufen. Die gemessenen DELTAS bleiben gueltig, weil beide Arme jeweils
  identisch parametrisiert waren; die ABSOLUTEN Titelzahlen (370 / 373 / 1443 / 2823) weichen
  von einem App-Lauf mit Defaults ab. Wer die Zahlen reproduzieren will, muss beide Parameter
  mitsetzen. Der asymmetrische Size Buffer war dagegen eine bewusste Wahl, weil er Nicos
  Backtest-File reproduziert (App-Default ist Symmetrisch).

- **2026-08-25, ATVR-Regel final: nur der teure Ast ist scharf.** Entscheidung Nico nach der
  Messung. Stand:

  | Kurs | ADTV (unveraendert) | ATVR |
  |---|---|---|
  | < 20.000 USD | 1 Mio neu / 750k Bestand, 3M + 6M | **keine Anforderung** |
  | >= 20.000 USD | identisch | **10 % neu / 5 % Bestand** |

  Gemessen als `min(ATVR 3M, ATVR 6M)`, annualisiert. Kein Titel faellt mehr wegen des Kurses
  allein; ab 20.000 faellt nur, wer zusaetzlich die ATVR reisst. Der ATVR-Screen laeuft dafuer
  jetzt auf 3M/6M statt 3M/12M (mit Schwelle 0 verhaltensneutral, mit Schwellen > 0 nicht,
  deshalb explizit getestet).
  **Abnahme, 48 Perioden:** NX-EU-LM 372 -> 373, NX-DM-LM 1.442 -> 1.443, NX-EM-LM unveraendert,
  NX-GM-LM 2.822 -> 2.823. Zugaenge Berkshire A und Lindt-Namenaktie, Abgang Dollar Tree
  (Verdraengung durch Berkshire As Float in der Coverage-Treppe). Turnover unveraendert.
  **Indische Abgaenge: 0.**

  **Warum der normale Ast auf 0 bleibt.** Nicos Vorschlag war 2,00 % neu / 1,50 % Bestand. Am
  Snapshot 2026-08-19 sah das sicher aus (indisches Minimum 2,49 %, also Faktor 1,66 Abstand zur
  Maintenance-Schwelle). Ueber die HISTORIE nicht: Indiens Minimum sinkt auf **0,45 %**
  (2023-05-17), und 28 von 48 Perioden haben mindestens einen Titel unter 1,5 %. Erst-Effekt der
  Schwellen waeren **62 Titel-Perioden-Paare auf 13 verschiedenen Titeln** (mit Kaskaden 87):
  HDFC Bank in 20 Perioden, ICICI Bank 7, ITC 7, HDFC Ltd 6, Axis Bank 4, Kotak 3, Reliance
  Industries 3, Sun Pharma 3, dazu L&T, Bharti Airtel, Hindustan Unilever, UltraTech, Infosys.
  Ursache ist die BSE-Datenlage (rund 1/10 des NSE-Umsatzes), die Kennzahl misst dort einen
  Datenfehler. Eine Schwelle unter 0,45 % trifft global nichts mehr.
  Die Felder sind da und dokumentiert, einschalten sobald Indien ueber NSE gezogen wird.
  Lehre: **Schwellen nie am Snapshot kalibrieren.** Der letzte Stichtag war um Faktor 5,5 zu
  optimistisch gegenueber dem historischen Minimum.

  Nebenbefund aus dem Lauf mit scharfem normalem Ast: faellt Banorte weg, kommen **19 mexikanische
  Titel** neu in NX-GM-LM. Banortes FF MCap ist kaputt (1.430 Mrd gegen 30,6 Mrd Total MCap,
  Verhaeltnis 46,67 statt 0,86) und blaeht Mexikos Coverage-Nenner auf, was legitime Mid Caps nach
  Small drueckt. Gehoert ueber In-Eligible oder eine Float-Korrektur behandelt, NICHT als
  Nebeneffekt einer Liquiditaetsregel. OFFEN.

  Verifiziert: Regression 231/231 (davon 24 neue Faelle: Vier-Zellen-Matrix, Indien-Schutz mit
  Grasims 2,494 %, echte Snapshot-Zahlen fuer Berkshire/Lindt/Golfclub, 3M/6M-Beine,
  Neutralitaet bei Schwelle 0), AppTest ohne Exception, ruff sauber.

- **2026-08-25, Max Price: harter Ausschluss -> ATVR-Bedingung.** Ein Titel mit Kurs
  >= 20.000 (Handelswaehrung) faellt nicht mehr raus, sondern muss
  **min(ATVR_3M, ATVR_6M) >= 0,3 %** erfuellen. Gleiche Schwelle fuer neue UND bestehende
  Mitglieder, kein Maintenance-Rabatt (Vorgabe Nico).
  `ATVR_6M` gab es in der Engine nicht (nur 3M und 12M), ist ergaenzt mit derselben
  Fallback-Kette (6M -> 3M -> 1M). Rein additiv, der regulaere Liquiditaets-Screen laeuft
  weiter auf 3M und 12M.
  Der Test musste von `apply_universe_exclusions` (Step 3) an die Liquiditaetsstufe wandern,
  weil die ATVR vorher nicht existiert. Sidebar: Umschaltung "Ausschluss (bisher)" /
  "ATVR-Bedingung" plus Schwellenfeld, Default ATVR-Bedingung mit 0,3 %. Beides im
  Settings-Stempel.
  Betroffen sind global genau 5 Titel (Snapshot 2026-08-19): Berkshire Hathaway A
  (ATVR 14,1 %, 242 Mrd FF), Lindt-Namenaktie (32,1 %, 12,7 Mrd), Turkiye Is Bankasi A
  (0,000 %), ISKUR (0,055 %), Club de Golf Santiago (0,000 %). Die Regel trennt drei
  Groessenordnungen auseinander, die Schwellenwahl ist also unkritisch.
  **Gemessen, 48 Perioden Europe Pooled, MIT max_price=20000:** NX-EU-LM 372 -> 373,
  NX-DM-LM 1.442 -> 1.443, NX-GM-LM 2.822 -> 2.823, alle 48 Perioden betroffen.
  NX-EU-LM gewinnt LISN-SWX. NX-DM-LM gewinnt BRK.A und LISN und verliert DLTR-USA
  (Dollar Tree) - reiner Verdraengungseffekt, Berkshire As 242 Mrd verschieben die
  Coverage-Treppe.
  Nebeneffekt geprueft: es sind jetzt BEIDE Aktiengattungen einer Firma im Index moeglich
  (Lindt Namenaktie + Partizipationsschein, Berkshire A + B, jeweils gleiche Entity ID).
  Bei Lindt ist das MSCI-konform, MSCI Europe haelt beide Linien (LISN 0,08 %, LISP 0,07 %).
  Fuer Berkshire liegen keine Benchmark-Daten vor (MSCI_CHECK ist Europa).
  Nebenbefund: LISN war einer der 55 MSCI-Only-Titel, die Regel schliesst diese Luecke.
  OFFEN: Schwelle 0,3 % oder 0,03 %? Nicos Notation war doppelt. Unterschied ist genau ein
  Titel (ISKUR bei 0,055 %). Default steht auf 0,3 %.
  Tests: 15 neue Faelle mit den echten Snapshot-Zahlen, darunter "kein Maintenance-Rabatt
  fuer Bestandstitel" und die Neutralitaet ohne die neuen Argumente. Regression 210/210.

- **2026-08-25, WICHTIG fuer alle heutigen Messungen: meine Analyse-Skripte liefen mit
  `max_price=None`**, die App hat 20.000 als Default. Die gemessenen DELTAS bleiben gueltig
  (beide Arme identisch parametrisiert), die absoluten Titelzahlen weichen aber ab. Das
  erklaert auch, warum die Lindt-Namenaktie in meinen Laeufen ueber alle 48 Perioden im Index
  war, in Nicos Backtest-File aber nicht: Ursache war der Preis-Filter, nicht die Methodik.
  Die Abnahme der Max-Price-Regel lief bewusst MIT max_price=20000.

- **2026-08-25, ADTV-Ausnahme auf HORIZONT umgebaut (Nicos Einwand, er hatte recht).**
  Die erste Version galt nur am Seed-Termin. Nico hat aufgezeigt, dass damit der FOLGETERMIN
  offen bleibt: bei Quartals-Rhythmus und Ex-Date 2025-12-08 liegt der zweite Termin
  5,4 Monate danach, das 3M-Fenster ist dann voll, das **6M-Fenster noch nicht**. Fehlt der
  6M-Wert dort, scheitert das Kind an einer Huerde, die es rechnerisch nicht erfuellen kann,
  faellt aus `gm_complete`, verliert den geerbten Bestandsschutz und ist dauerhaft ausgesperrt.
  Genau die Klippe, die die Ausnahme schliessen sollte, nur eine Periode spaeter.
  Neu: `spinoff_liquidity_exemptions()` leitet die offenen Horizonte aus dem **Ex-Date** ab.
  Ein Horizont ist offen solange `selection_date < ex_date + N Monate` (N = 3 / 6 / 12,
  strikt kleiner). `apply_liquidity_new` nimmt bei `exempt_missing_keys` jetzt ein Dict pro
  Horizont ODER weiterhin ein flaches Set (rueckwaertskompatibel, Alt-Tests unveraendert
  gruen). Zuordnung: 3M ADTV und ATVR_3M -> "3M", 6M ADTV -> "6M", ATVR_12M -> "12M".
  Kein neuer Tunable-Parameter, die Grenze kommt aus dem Ereignisdatum.
  Berechtigt ist nur ein Kind, das gerade geseedet wird oder schon Bestandstitel ist, damit
  ein verworfener Seed keine Liquiditaets-Erleichterung durch die Hintertuer bekommt.
  Sichtbarkeit: das Protokoll bekommt Zeilen mit Status `Ausnahme aktiv` fuer Perioden ohne
  Seed, in denen ein Horizont noch offen ist. Ohne das waere die Wirkung am Folgetermin
  unsichtbar.
  **Abnahme mit vorab festgelegter Erwartung getroffen:** Magnum-Simulation mit allen
  ADTV-Spalten leer am Seed-Termin UND 6M/12M leer am Folgetermin -> durchgehend Mid Cap und
  im Index, 379 / 375 / 373 Titel, identisch zum Normalfall. Mit dem Vorgaengerstand waere es
  am 2026-05-20 rausgefallen.
  Tests: 15 neue Faelle, darunter die Horizont-Fenster ueber fuenf Termine, die exakten
  Grenzen (genau 3 bzw. 6 Monate nach Ex-Date ist der Horizont ZU), die Berechtigung
  (ohne Seed und ohne Bestand nichts, vor dem Seed-Termin nichts), und dass die Dict-Form
  nur das jeweils offene Bein oeffnet. Regression 195/195.

- **2026-08-25, ADTV-Ausnahme zunaechst nur am Seed-Datum (ueberholt, siehe Eintrag darueber).** Gemeint war
  nicht ein pauschales Ignorieren, sondern: fehlt das 3M-/6M-ADTV, wird es beim geseedeten Kind
  an seinem ersten Selection Date ignoriert. Umgesetzt als `liquidity_exempt_missing` in
  `run_selection_pipeline` -> `exempt_missing_keys` in `apply_liquidity_new`.
  Der Grund dafuer war staerker als ich zuerst dachte. Simulation (Magnums ADTV am 2026-02-18
  auf NaN, voller 48-Perioden-Lauf): das Kind scheitert am Screen, landet nicht in
  `gm_complete`, und weil der Incumbent-State der Folgeperiode aus `gm_complete` neu aufgebaut
  wird, ist es 2026-05-20 **kein Bestandstitel mehr**. Es kommt als Neuzugang gegen den glatten
  85er-Schnitt, wird bei Coverage 88,73 Small Cap und bleibt es. Ein einzelner fehlender
  Datenpunkt sperrt den Titel also DAUERHAFT aus, nicht nur eine Periode. Mit der Ausnahme ist
  der Verlauf identisch zum Normalfall (Mid Cap, im Index, 373 Titel am 2026-08-19).
  **Fallstrick, der die erste Version wirkungslos machte:** `build_new_universe` macht
  `pd.to_numeric(...).fillna(0)` auf alle vier ADTV-Spalten. Im Screen kommen fehlende Werte
  als 0.0 an, NaN und echte Null sind nicht unterscheidbar. Eine Pruefung nur auf `isna`
  konnte nie feuern (per Trace bestaetigt: Werte kamen als 0.0 rein). Bedingung ist jetzt
  NaN **oder <= 0**. Ein vorhandener Wert oberhalb 0 aber unter der Schwelle schliesst weiter
  aus. Damit ist auch ein echter Null-Umsatz-Stumpf abgedeckt, der laeuft in der Folgeperiode
  gegen die normale Maintenance-Schwelle.
  Auf den echten Daten aendert die Ausnahme NICHTS (FactSet fuellt auf, sie feuert nie), sie
  ist Versicherung gegen einen seltenen, aber dauerhaften Schaden. Das Protokoll hat dafuer
  die Spalte `ADTV-Ausnahme` ("greift (3M + 6M fehlt)" / "nicht nötig").
  Tests: 10 Faelle, darunter 0.0 greift mit Ausnahme / scheitert ohne, vorhandener Wert unter
  Schwelle scheitert weiter, ein fehlender plus ein zu kleiner Horizont scheitert,
  Bit-Neutralitaet bei leerer Ausnahme-Menge. Regression 180/180.

- **2026-08-25, ERSTE Einschaetzung zum 3M-ADTV, spaeter revidiert (siehe Eintrag darueber).** Nicos Frage war, ob ein Kind
  mit weniger als drei Monaten Handelshistorie das 3M-ADTV vernachlaessigen darf. Geprueft und
  bewusst NICHT gebaut, aus zwei Gruenden.
  Erstens: der Wert fehlt nicht. FactSet fuellt die laengeren Horizonte mit dem verfuegbaren
  Fenster auf. Magnum hat am 2026-02-18 1M=39,94 / 3M=6M=12M=64,53 Mio; Italgas neun Tage nach
  dem Listing 1M=3M=6M=12M=78,33 Mio. Im ganzen `gm_complete` gibt es null NaN in den
  ADTV-Spalten.
  Zweitens: der aufgefuellte Wert ist zu HOCH, nicht zu niedrig. Magnums 3M-ADTV faellt von
  64,53 Mio in der ersten Periode auf 35,66 Mio in der naechsten, das Spin-off-Fenster ist
  durch Indexfonds- und Arbitrage-Volumen um rund 80 % ueberzeichnet. Eine Ausnahme wuerde
  also eine Pruefung ausschalten, die momentan zu leicht durchlaesst.
  Nebenbei: der Screen testet vier Groessen (3M ADTV, 6M ADTV, ATVR_3M, ATVR_12M), eine
  Ausnahme haette alle vier betreffen muessen.
  Stattdessen gebaut: das Seed-Protokoll zeigt jetzt die Spalte **Segment nach Lauf**
  (`_spinoff_outcome`). Damit ist sichtbar, ob ein Seed gegriffen hat (Large/Mid), geseedet
  aber nicht im Standard gelandet ist (Small/Micro) oder an einem Screen gescheitert ist
  (nicht im Lauf) - und zwar fuer JEDE Ursache, nicht nur fuer fehlendes ADTV.

- **2026-08-25, Spin-off-Aufnahme umgesetzt.** Ein aus einem Indexmitglied abgespaltener Titel
  kommt beim Ereignis als BESTANDSTITEL in den Index und muss die Entry-Schwellen nie
  durchlaufen; er erbt das Segment der Mutter und wird ab derselben Periode mit
  Maintenance-Schwellen und Size-Hysterese geprueft. Einmaliger Seed, kein Dauerprivileg,
  kein Verfallsdatum (Entscheidung Nico).
  Engine: `load_spinoff_list()` + `seed_spinoff_incumbents()` in `pipeline_core.py`, beide
  Streamlit-frei. An `run_selection_pipeline` musste NICHTS geaendert werden, weil
  Bestandsschutz dort nur ein Set plus ein Dict ist, die die Run-Schleife uebergibt.
  Bewusst KEINE Mindestgroessen-Klammer: der Seed laeuft in derselben Periode gegen die
  Maintenance-Schwellen, ein zu kleiner Stumpf wird ohnehin Small Cap. Die Regel begrenzt
  sich selbst. Belegt an Italgas (siehe unten).
  Verdrahtet in den DREI Incumbent-States, die auf `run_selection_pipeline` laufen:
  Multi-Period Haupt, Multi-Period Total-Markets, Europe MP (Pooled).
  OFFEN: Helvetica MP fehlt noch. Es nutzt `build_helvetica_pipeline` und schluesselt auf
  `Entity ID`; `seed_spinoff_incumbents` kann das per `key_fn` (getestet), die Verdrahtung
  in der Helvetica-Schleife ist aber nicht gemacht.
  Sichtbarkeit: Spalte `Spinoff_Seeded` auf den Konstituenten, Spalte `Spin-off-Seeds` in der
  Summary, Sheet `Spin-offs` im Long-Export mit dem Protokoll je Eintrag, Expander im
  Ergebnisblock, Eintrag im Settings-Stempel. Sidebar-Toggle Default an (leere Liste = No-op).
  **Abnahme mit vorab festgelegter Erwartung getroffen**: Europe MP (Pooled), 48 Perioden,
  asym 5 pp, NX-EU-LM **370 -> 371**. Nur Magnum Ice Cream (Unilever, Seed 2026-02-18) kommt
  dazu (Coverage 88,73 %, von der Hysterese gehalten). Italgas (Snam 2016) wird geseedet,
  bleibt aber wirkungslos (Coverage danach durchgehend > 90). Sandoz (Novartis 2023) hatte die
  Entry-Schwellen selbst geschafft und war ab 2023-11-15 ohnehin drin. "geseedet" im Protokoll
  heisst also: Seed angewandt, nicht Seed noetig.
  Tests: 21 neue Faelle, darunter die Neutralitaetszusage (leere Liste / anderer Termin /
  None lassen den State bit-identisch), Segment-Vererbung, Override, vier Verwerfungsgruende
  und die `key_fn`-Variante fuer Helvetica. Regression 166/166, AppTest in beiden Data-Modes
  ohne Exception, ruff sauber.
  Doku: eigener Abschnitt in `NaroIX_Europe_Global_Index_Guideline.md` (Kapitel 5) und in
  `MULTI_PERIOD.md`.

- **2026-08-25, Master ist ein rechteckiges Panel.** Beim Bauen des Validators aufgefallen und
  wichtig fuer jede kuenftige Praesenzpruefung: JEDE ISIN hat in JEDER der 48 Perioden eine
  Zeile, die Werte sind bis zum Listing leer. Magnum hat `Total MCap` erst ab 2026-02-18,
  Italgas erst ab 2016-11-16, die Zeile existiert aber seit 2014-11-19. Auf Zeilen-Existenz
  zu pruefen sagt also immer "ja". Richtiges Kriterium ist "erste Periode mit
  Total MCap > 0". Meine erste Validator-Version hat deswegen bei jedem Eintrag falsch
  gewarnt.

- **2026-08-25, `Spin-Off Data.xlsx` geprueft.** Drei Eintraege (Italgas/Snam 2016-11-16,
  Sandoz/Novartis 2023-11-15, Magnum/Unilever 2026-02-18), alle datumsgenau korrekt: Seed-Termin
  ist jeweils der erste Selection Date nach dem Ex-Date und gleichzeitig die erste Periode mit
  Daten, und alle drei Muetter waren in der Vorperiode im investierbaren Universum.
  OFFEN: die Spalte `Quelle` ist in allen drei Zeilen leer. Der Loader meldet das als
  nicht-blockierenden Hinweis. Solange sie leer ist, ist die Liste von "aus den heutigen
  MSCI-Holdings abgeschrieben" nicht unterscheidbar, und alle drei Titel sind heute
  MSCI-Mitglieder. Ex-Date plus Quelle sind die Verteidigung gegen den Look-ahead-Vorwurf.
  Kleinkram: das Sheet `Glossar` hat einen kaputten Header (erste Spec-Zeile ist zur
  Spaltenueberschrift geworden), rein kosmetisch, der Loader liest nur das Sheet `Spin-Off`.

- **2026-08-25, vier UI-Punkte umgesetzt (Reproduzierbarkeit + Size-Buffer).**
  1. **Settings-Stempel.** `_settings_snapshot()` friert 34 laufrelevante Parameter BEIM LAUF ein
     (nicht beim Export), liegt als Sheet `Settings` in Long-/Wide-/Segment-Export und im
     Detail-Download, und wird im Ergebnisblock als Expander gezeigt. Anlass: es hat drei volle
     48-Perioden-Laeufe gekostet, um herauszufinden, mit welchen Settings ein vorhandener
     Backtest erzeugt wurde.
  2. **Stale-Guard** fuer Multi-Period UND Europe MP (gab es vorher nur bei Helvetica MP).
     `_settings_diff()` vergleicht Lauf-Snapshot gegen aktuelle Sidebar und zeigt eine
     Warnung samt Tabelle der geaenderten Parameter. Bewusst OHNE die Ergebnisse zu verwerfen
     (anders als Helvetica MP): ein 48-Perioden-Lauf ist zu teuer, um ihn wegen eines Klicks
     zu killen.
  3. **Getrennte Bandbreite fuer die Mid/Small-Kante** (`size_buffer_pp_ms`). Die Engine konnte
     das schon, die UI hat den Parameter nie uebergeben. Feld erscheint nur im FTSE-Modus
     (nur `_size_segment_entry` wertet es aus), Default = gleiche Breite wie oben.
     Verifiziert ueber 48 Perioden: ms=None und ms=5 sind identisch (verhaltensneutral);
     ms=6 bringt NX-EU-LM von 370 auf 388 bei NULL Large/Mid-Umsortierungen, waehrend der
     grobe Hebel (beide Kanten 6 pp) dieselben 388 mit 171 Umsortierungen erkauft.
  4. **Schwellen-Tabelle je Buffer-Variante** als Expander nach der Modus-Wahl, mit Markierung,
     welche Kante ueber die Index-Zugehoerigkeit entscheidet und welche nur ueber die
     Sub-Index-Zuordnung. Ausserdem entschaerft: die Caption ueber dem Modus-Radio rendert
     rund 100 Zeilen VOR der Modus-Wahl und behauptete die symmetrische Lesart
     ("Mid zwischen 65-90 %"), was im FTSE-Modus falsch ist (dort 70).
  Nicht angefasst: Punkt 5 (Benchmark-Abgleich als Feature) und Punkt 6 (zwei Laeufe
  nebeneinander) der Liste, beides groessere Features.
  Verifiziert: Regression 145/145, AppTest in beiden Data-Modes ohne Exception, ruff sauber,
  Smoke-Test prueft explizit, dass das Settings-Sheet den LAUF zeigt und nicht die Sidebar.

- **2026-08-24, Band 85-91 ist im Pooled-Lauf gezielt, aber ein globaler Hebel.** Sensitivitaet
  um die Oberkante (volle Laeufe): 85-90 haelt 0 von 35, 85-90,5 haelt 7 (380 Titel), 85-91 haelt
  15 (388), 85-91,5 haelt 16 (390). Der Gewinn saettigt also direkt hinter 91. Sauber daran:
  "nur MSCI" faellt 56 -> 39, "nur wir" steigt nur 30 -> 31, Gewichtsabdeckung 97,41 -> 98,13 %,
  EU-Turnover 3,9 -> 3,6 %. Preis: `size_buffer_pp` ist global, NX-DM-LM waechst 1439 -> 1509
  (+70) und NX-GM-LM 2799 -> 2937 (+138). 15 Europa-Titel kosten 138 globale.
  Einschraenkung: die 35 wurden ueber genau diese 90er-Kante definiert, das Retention-Mass ist
  also teilweise zirkulaer. Unabhaengig ist nur der "nur wir"-Wert (+1), und der bestaetigt, dass
  es gezielt wirkt. Echtes Out-of-Sample gegen MSCI ist nicht moeglich, es liegt nur der aktuelle
  MSCI-Holdings-Stand vor, keine Historie.

- **2026-08-24, der Baseline-Lauf je Land matcht MSCI SCHLECHTER als der gepoolte.** Erstmals
  direkt gegengerechnet, gleiche Settings, nur `europe_pool` umgeschaltet. Baseline 85-90:
  NX-EU-LM 428 Titel, aber nur 334 MSCI-Treffer, 62 nur MSCI, 94 nur wir, Gewichtsabdeckung
  96,49 %. Gepoolt 85-90: 370 Titel, 340 Treffer, 56 nur MSCI, 30 nur wir, 97,41 %. Der gepoolte
  Lauf trifft also mit 58 Titeln WENIGER mehr MSCI-Gewicht. Baseline mit 85-91: 440 Titel,
  97,06 %, nur wir 98 - liegt damit noch unter dem gepoolten Ist-Stand.
  Ausserdem: 19 der 35 Abgaenge sind im Baseline-Lauf noch drin, ihr Abgang ist also reiner
  Pooling-Effekt; die anderen 16 fallen auch je Land raus.

- **2026-08-24, MSCI-Abgleich: die Abgaenge sind Groesse, nicht Float.** Gegen `MSCI_CHECK.xlsx`
  (ETF-Holdings MSCI Europe, 396 Titel) und den Europe-Pooled-Backtest 2014-11-19 bis
  2026-08-19: Overlap 341, 35 waren mal drin und sind jetzt raus, 19 stehen im Master und waren
  nie drin, 1 echte Datenluecke (Octave Intelligence SDR). Gewichteter Overlap 97,4 %.
  Diagnose der 35 (voller Pipeline-Nachbau, 35/35 mit identischem Abgangstermin reproduziert):
  ausnahmslos Mid Cap -> Small Cap, Coverage `_c_before` springt von 86,8-90,0 auf 90,06-94,02.
  Kein einziger scheitert an Float oder Liquiditaet (alle im liquiden Pool, FF% danach >= 33,7,
  Median delta FF 0,0 pp, 27 von 35 unter 1 pp Bewegung). Total MCap faellt im Median 13,5 %,
  gleichzeitig steigt der gepoolte Europa-Cutoff von 7,33 auf 8,61 Mrd USD. Sie hingen also
  schon im Hysterese-Band und die 90er-Oberkante ist gerissen. Bei den 19 dasselbe Bild
  (Coverage 85,9-91,8, kein Float-/ADTV-Fail); Ausnahmen sind SUNB-USA und AER-USA
  (Mapping Country US) und CSG-AMS (Mapping Country CZECH REPUBLIC = EM).
  Buffer-Frage, volle Laeufe je Variante (Pfadabhaengigkeit): nur das Aufweiten der Mid/Small-
  Oberkante haelt sie. Band 85-90 (Baseline) 0 von 35, 85-91 15, 85-92,5 29, 85-95 34.
  Symmetrisch 80-90, MSCI Logic (-33/+50) und Size Integrity halten jeweils 0. MSCI Logic
  verschlechtert den Match sogar (94,91 % Gewicht statt 97,41 %). Effizientester Punkt ist
  Band 85-92,5: 408 Titel (MSCI: 396), 98,68 % Gewicht, nur MSCI faellt von 56 auf 25, nur wir
  steigt nur von 30 auf 37, Turnover sinkt von 3,9 auf 3,3 %. Bei 85-95 kippt es (nur wir 76).
  WICHTIG: ein breiteres Hysterese-Band ist NICHT MSCIs Mechanismus. Keine Methodikaenderung
  beschlossen, das ist reine Diagnose.
  Nebenbefund: der Europe-Pooled-Backtest des Nutzers lief mit dem ASYMMETRISCHEN Size Buffer,
  nicht mit dem Default Symmetrisch. Symmetrisch ergibt 339 statt 374 Titel; asymmetrisch
  trifft 370 von 374 (max. Abweichung 4 Titel ueber 48 Perioden).
  Ergebnisse: `MSCI_vs_NX-EU-LM_Pooled_Abgleich.xlsx`, `MSCI_Abgaenge_Diagnose.xlsx`.

- **2026-08-24, Europe MP (Pooled) nutzt den Multi-Period-Ergebnisblock.** Der komplette
  Nach-Lauf-Block ist als eine Funktion `render_mp_results(prefix, file_tag, extra_cols,
  caption_extra)` in [naroix_benchmark.py](naroix_benchmark.py) herausgezogen und wird von
  beiden Tabs aufgerufen (`"multi"` / `"eupool"`). Enthalten: Detail-Ansicht mit Investable
  Universe, DM/EM-Country-Breakdown, Land-/Sektor-Charts, Index Characteristics, der lazy
  Export ("Downloads vorbereiten" -> Long / Gewichtsmatrix / Backtest / Segment-Wanderung),
  Gewichtsmatrix mit Kennzahlen, Segment-Wanderung, Country-/Sector-Gewichte ueber Zeit und
  Tenure. `_mp_build_export_bytes(prefix)` ist ebenfalls prefix-faehig.
  Statt zwei getrennt gepflegter Bloecke gibt es damit nur noch einen; die Tabs bleiben ueber
  getrennte Session-State-Prefixe voneinander unabhaengig (`multi_*` vs `eupool_*`), der
  Europe-Pooled-Lauf schreibt zusaetzlich `eupool_eumss`, `eupool_si`, `eupool_wide` und
  `eupool_segmatrix` mit und verwirft stale Export-Bytes.
  Dateinamen: Multi-Period unveraendert, Europe MP traegt `EuropePooled_` bzw.
  `NaroIX_EuropePooled_*`, damit ein NX-EU-LM aus dem Pooled-Lauf nicht wie eines aus dem
  Baseline-Lauf heisst. Tab-eigene Bloecke (Summary je Periode, Cutoff-Chart,
  Konstituenten je Land) bleiben; der Pool-Cutoff der gewaehlten Periode haengt via
  `caption_extra` weiter an der Detail-Caption.
  Verifiziert: Regression 145/145 PASS, Streamlit-AppTest ohne Exception, plus ein
  Smoke-Test, der den Block fuer beide Prefixes gegen synthetische Laufergebnisse rendert
  (je 8 Downloads, 3 Charts, 9 Tabellen, alle 4 Export-Dateien nicht leer).

- **2026-08-23, NAICS-Fondsfilter entfernt.** Der Filter "NAICS enthaelt Open-End Investment
  Fund" ist komplett aus dem Code raus (Funktion, Sidebar-Toggle, Exclusion-Summary, alle
  Signaturen). Grund: das FactSet-Feld markiert operative Asset Manager als Fonds. Von 16
  Treffern im Master 05/2026 waren 10 operative Firmen (WisdomTree, Jupiter Fund Management,
  IntegraFin, Strive, Groww, City of London Investment Group u.a.). `Sec Type` diskriminiert
  nicht (alle SHARE), Name-Regex ebenfalls nicht.
  Verifiziert am Snapshot 2026-05-20: 15 der 16 Titel sind jetzt im Universe, davon 6 in IMI
  (Groww EM Mid, WisdomTree/IntegraFin/Strive/Jupiter/Y.D. More DM Small). Die echten
  Fondsvehikel und der SPAC landen alle in Micro Cap, also ausserhalb der Indizes. Kein
  In-Eligible-Eintrag notwendig.
  Regression: 138/138 PASS (inkl. Integrationstests auf dem echten Master).

## Offene Methodikfrage: label_before_liquidity (2026-09-05)

Anlass: Anbietervergleich der Selektionskette gegen die aktuellen Regelwerke (MSCI GIMI 05/2026,
FTSE GEIS v14.3, Solactive GBS v3.05, STOXX IMI 08/2026, Morningstar TME, Bloomberg GEI 06/2026).
Artefakt: https://claude.ai/code/artifact/91a2dde0-d0e8-40f8-bca2-821ce54212b1

Frage: Segmentierung VOR oder NACH dem Liquiditaetsscreen. Default ist nach (Waterfall auf `gm_liq`).
Nico weist darauf hin, dass die Methodik noch nicht live und damit nicht fixiert ist.

Stand der Regelwerke: 5 von 6 segmentieren nach dem Screen wie wir. Nur FTSE stellt den Nenner
(Index Universe, Top 98 %) in Regel 7.3 VOR die Screens aus Abschnitt 6. FTSE kumuliert dabei
aber volle MCap, nicht Float.

Messung 1, Einzelperiode 19.08.2026 ohne Buffer, ohne Pooling, global:
- 727 illiquide Titel kommen unter B in den Nenner (Pool 9.390 -> 10.117)
- Standard (L+M) 2.500 -> 2.599 (+99), Small -99, Micro unveraendert
- 183 Segmentwechsel, davon 178 nach oben (101 Small->Mid, 77 Mid->Large), 5 nach unten
- Standard deckt vom investierbaren Universum 85,19 % -> 85,51 % (+0,32 pp)
- Produkte: NX-GM-LM +99, NX-DM-LM +20, NX-EU-LM (ungepoolt) +12
- Verhaeltnis: +4 % Konstituenten fuer +0,32 pp Coverage, die neuen Titel tragen im Schnitt
  ein Zehntel eines durchschnittlichen Standard-Konstituenten

Messung 2, Europe Pooled, volle 48 Perioden, Config = P-Dict aus `run_eupool.py`,
Endperiode 19.08.2026 gegen MSCI Europe (396 ISINs, 99,66 % Gewicht):

| | A Default | B label first |
|---|---|---|
| Konstituenten | 403 | 429 |
| Treffer in MSCI | 365 | 382 |
| in MSCI, bei uns nicht | 31 | 14 |
| bei uns, nicht in MSCI | 38 | 47 |
| Namens-Overlap | 92,2 % | 96,5 % |
| Gewichteter Overlap | 98,54 % | 99,13 % |

B holt 17 MSCI-Titel zusaetzlich herein und verliert KEINEN. Die 17 sind alle klein
(0,02 bis 0,06 % MSCI-Gewicht, zusammen 0,59 %): Trelleborg B, Securitas B, Spirax, Zalando,
Italgas, Hensoldt, Land Securities, Beijer Ref, InPost, Tubize, Balder, Barry Callebaut,
Demant, Ayvens, Rockwool und zwei weitere. Preis: 9 zusaetzliche Titel, die MSCI nicht haelt.

Bewertung, noch nicht entschieden:
- FUER B: streng dominant auf der Trefferseite (17 gewonnen, 0 verloren), fehlendes MSCI-Gewicht
  halbiert (1,46 % -> 0,87 %), entkoppelt die Segmentgrenzen davon, ob fremde Titel liquide sind.
- GEGEN B: die Paarung "min(Float, FOL)-Nenner + ungefilterter Pool" fahrt kein Anbieter.
  FTSE ist kohaerent, weil dort volle MCap kumuliert wird. Das ist der einzige verbliebene Einwand.
- ZURUECKGEZOGEN (2026-09-05, Nachrechnung): das Argument, IF-0-Titel wuerden aus dem Nenner
  geworfen waehrend illiquide unter B voll mitzaehlten, war falsch. Adj_FF von IF-0-Titeln ist
  definitionsgemaess 0, sie tragen also weder zu `tot` noch zum cumsum bei. Ihr Ein- oder
  Ausschluss aus dem Waterfall-Pool ist arithmetisch ein No-op fuer jeden anderen Titel. Der
  Ausschluss in `pipeline_core.py` dient dem Label ("Non-Investable" statt einer Groessenklasse)
  und dem tot==0-Guard, nicht der Nenner-Korrektur. Gemessen 19.08.2026: 20 Adj_FF-0-Zeilen im
  Universe (36.122), davon genau 1 nach EUMSS (Gulf International Services QSC, Qatar,
  Industry-FOL 0), 0 Laender mit Pool-Summe 0, 0 davon illiquide.
- Folgefrage von Nico (EUMSS -> label first -> IF-0-Ausschluss zuletzt): heute ein No-op, es
  aendert nur die Buchhaltung zum Schlechteren (der eine Titel bekaeme eine Groessenklasse statt
  "Non-Investable"). RELEVANT wird die Reihenfolge erst bei Nenner = Total MCap, denn dort sind
  IF-0-Titel nicht mehr gewichtslos: der Qatar-Titel traegt 0,57 % der Total MCap seines Landes.
  In der Total-MCap-Variante ist Nicos Reihenfolge die FTSE-konforme.
- Der gewichtete Overlap war schon unter A bei 98,54 %. B verbessert vor allem die Namensanzahl,
  also genau die Metrik, die wir im Kundencall bewusst NICHT fuehren wollten.
- `label_before_liquidity` ist global, nicht EU-spezifisch: der EU-Gewinn kostet +99 Titel in
  NX-GM-LM und +20 in NX-DM-LM, dort ohne Benchmark, gegen den sich das bewerten liesse.

Messung 3 (2026-09-05), Europe Pooled, 48 Perioden, vier Varianten, Endperiode gegen MSCI Europe.
ACHTUNG Vergleichbarkeit: Messung 2 lief mit `size_buffer_pp_ms=7.0` (Default von `run_eupool.py`),
Messung 3 mit 5.0 (guideline-konform, Halteseite 75/90/99,5). Deshalb liegen A und B hier tiefer als
in Messung 2 (A 403 -> 375, B 429 -> 394). Die Mid/Small-Bandbreite ist ein starker Hebel auf das
Niveau; die Deltas zwischen den Varianten bleiben richtungsgleich.

| | A Default | B Label first | C + Total MCap | D FTSE-nah |
|---|---|---|---|---|
| Reihenfolge | Liq. zuerst | Label zuerst | Label zuerst | Label zuerst |
| Nenner | min(Float,FOL) | min(Float,FOL) | Total MCap | Total MCap |
| Schwellen | 70/85/99 | 70/85/99 | 70/85/99 | 68/86/98 |
| Halte-Buffer | 75/90/99,5 | 75/90/99,5 | 75/90/99,5 | 72/92/101 |
| Konstituenten | 375 | 394 | 422 | 419 |
| Treffer in MSCI | 343 | 360 | 373 | 376 |
| in MSCI, uns fehlend | 53 | 36 | 23 | 20 |
| bei uns, nicht MSCI | 32 | 34 | 49 | 43 |
| Namens-Overlap | 86,6 % | 90,9 % | 94,2 % | 94,9 % |
| Gewichteter Overlap | 97,54 % | 98,27 % | 98,84 % | 99,01 % |
| fehlendes MSCI-Gewicht | 2,45 % | 1,72 % | 1,16 % | 0,99 % |
| Turnover, Wechsel/Periode | 14,0 | 15,0 | 15,5 | 14,6 |
| EUMSS-Boden | 759 Mio | 759 Mio | 759 Mio | 1.574 Mio |

Befunde:
- Monoton besserer Match A -> B -> C -> D auf jeder Metrik. Groesster Einzelhebel ist die
  REIHENFOLGE (A->B, fehlend -17), dann der NENNER (B->C, -13), dann die Schwellen (C->D, -3).
- D verliert gegenueber B KEINEN MSCI-Titel und holt 16 dazu (0,73 % Gewicht): Qiagen, Pandora,
  Rexel, Addtech B, Kingfisher, Securitas B, Melrose, SCA B, Indra, Spirax u. a.
- TURNOVER IST KEIN ARGUMENT GEGEN D: 14,6 vs 14,0 Wechsel/Periode bei A. Die offene Flanke aus
  Messung 2 ist damit geschlossen.
- Preis von C/D sind Nicht-MSCI-Titel: A 32, B 34, C 49, D 43. D ist effizienter als C.
- D verdoppelt den EUMSS-Boden (759 -> 1.574 Mio USD), weil `small_thr` bei uns BEIDES steuert,
  Small/Micro-Kante und EUMSS-Kalibrierungspunkt. D matcht also besser MIT kleinerem Universum.
- Restliche Fehlliste unter D wird von Laender-/Listing-Faellen dominiert, nicht von Groesse:
  Sunbelt Rentals (0,22 %), AerCap (0,16 %), Millicom, Abivax, Scout24, Land Securities, Beijer Ref,
  Zalando, Avolta, CTS Eventim. Der Segmentierungs-Hebel ist bei D weitgehend ausgereizt, der Rest
  haengt am Country-Mapping und an der Listing-Wahl.

Messung 4 (2026-09-05), Verlauf derselben vier Varianten ueber alle 48 Perioden:

| ueber 48 Perioden | A | B | C | D |
|---|---|---|---|---|
| Titel Median | 394 | 431 | 461 | 461 |
| Titel Spanne | 289-453 | 321-494 | 345-512 | 343-507 |
| Titel Mittel ggue. A | - | +36,6 | +63,0 | +61,9 |
| groesser als A | - | 48/48 | 48/48 | 48/48 |
| Turnover Mittel | 14,0 | 15,0 | 15,5 | 14,6 |
| Turnover Median | 14,0 | 15,0 | 15,0 | 14,0 |
| Turnover max | 35 | 27 | 27 | 25 |
| Turnover Summe (47) | 658 | 703 | 727 | 684 |
| Turnover in % der Titel | 3,6 % | 3,5 % | 3,4 % | 3,2 % |

- RANGFOLGE HAELT: A < B < C in 48 von 48 Perioden, ausnahmslos. Der Endstand ist kein guenstiger
  Stichtag. C und D liegen gleichauf (Median beide 461), D ist nur in 14/48 Perioden groesser als C.
- TURNOVER-AUSSAGE KORRIGIERT: absolut wechseln bei B/C/D mehr Titel, aber nur weil der Index
  groesser ist. Relativ zur Titelzahl dreht sich die Reihenfolge um, A ist mit 3,6 % am
  SCHLECHTESTEN, D mit 3,2 % am besten. Auch die schlimmste Einzelperiode liegt bei A (35 Wechsel
  gegen 25 bei D). Turnover ist damit kein Argument gegen die Umstellung, sondern eines dafuer.
- Einschraenkung bleibt: die Match-Kennzahlen sind eine Momentaufnahme zum 19.08.2026, weil nur ein
  MSCI-Europe-Stand vorliegt. Der Pfad ist ueber 48 Perioden gerechnet, die Bewertung nicht.
  Historische MSCI-Mitgliederlisten waeren noetig, um die Rangfolge auch im Match zu belegen.

Skripte: `cmp_trajectory.py` (Verlauf), `trajectory.csv` im Scratchpad.

Messung 5 (2026-09-05), A/B/C ueber 48 Perioden fuer vier Produkt-Konfigurationen
(`cmp_regions.py`, CSV `regions.csv`). Je Variante zwei Pipeline-Laeufe pro Periode, weil
europe_pool die ganze Kette betrifft; sechs getrennte Incumbent-Ketten.

| | Global A/B/C | Developed A/B/C | EU je Land A/B/C | EU gepoolt A/B/C |
|---|---|---|---|---|
| Titel Median | 2.996 / 3.289 / 3.870 | 1.708 / 1.854 / 1.945 | 451 / 492 / 510 | 394 / 431 / 461 |
| Mittel ggue. A | - / +288,5 / +717,7 | - / +119,3 / +206,1 | - / +41,0 / +55,6 | - / +36,6 / +63,0 |
| groesser als A | 48/48 beide | 48/48 beide | 48/48 beide | 48/48 beide |
| Turnover in % | 5,80 / 6,17 / 6,65 | 3,94 / 3,78 / 3,80 | 4,47 / 4,24 / 3,99 | 3,55 / 3,47 / 3,36 |
| Turnover max | 297 / 407 / 1026 | 149 / 151 / 145 | 39 / 47 / 39 | 35 / 27 / 27 |
| Standard-Coverage | 87,69 / 88,58 / 89,17 | 87,66 / 88,29 / 88,78 | 87,59 / 88,93 / 89,72 | 87,28 / 88,55 / 89,56 |
| MSCI Treffer | - | - | 334 / 342 / 353 | 343 / 360 / 373 |
| MSCI gew. Overlap | - | - | 96,49 / 97,02 / 97,68 | 97,54 / 98,27 / 98,84 |

BEFUNDE:
- C IST BLOCKIERT. Bei Global springt C am 2018-08-15 von 2.979 auf 3.869 Titel (+890 in einer
  Periode) und BLEIBT auf dem Niveau; A und B bewegen sich nur um +84. Dauerhafte
  Niveauverschiebung, kein Rebalancing-Ausschlag, erklaert den Turnover-max von 1.026.
  Geprueft und AUSGESCHLOSSEN: Klassifikationswechsel (keiner im Fenster) und die bekannten
  falschen Total-MCap-Werte aus `Incorrect_Hitstorical_Prices_and_Total_MCap.xlsx` (nur
  Venezuela/CARACAS, und Venezuela ist gar nicht klassifiziert). URSACHE OFFEN. Sie liegt in der
  Total-MCap-Spalte, dieselbe Periode auf Float-Basis ist unauffaellig. Vor einer Entscheidung
  fuer C muss das geklaert sein.
- B IST UEBERALL GUTARTIG. Relativer Turnover sinkt bei DM (3,94 -> 3,78), EU je Land
  (4,47 -> 4,24) und EU gepoolt (3,55 -> 3,47). Einzige Ausnahme Global: 5,80 -> 6,17.
  Titelzahl in 48/48 Perioden ueber A, in jeder Konfiguration.
- POOLING SCHLAEGT JE-LAND fuer Europa in JEDER Variante (gew. Overlap 97,54 vs 96,49 bei A,
  98,27 vs 97,02 bei B, 98,84 vs 97,68 bei C). Bestaetigt die Pooling-Entscheidung unabhaengig
  von der Reihenfolge-Frage.
- DIE 85 % STIMMEN SCHON HEUTE NICHT: bereits unter A deckt der Standard-Index 87,3-87,7 % des
  investierbaren Universums ab. Ursache ist die Straddle-Regel plus Size Buffer, nicht ein Fehler.
  Liegt im MSCI-Zielband 85 +/- 5. Unter B 88,3-88,9, unter C 88,8-89,7 (bei EU je Land 89,72,
  also fast an der Bandobergrenze). Fuer die Guideline-Kommunikation relevant.

STAND DER EMPFEHLUNG: B ist die einzige Variante, die heute ohne Code auskommt UND in allen vier
Konfigurationen unauffaellig ist. C bleibt bis zur Klaerung des 2018-Bruchs liegen. D erledigt.

Messung 6 (2026-09-05), Buffer-Variante x Coverage-Reihenfolge im Kreuz, Europe Pooled,
48 Perioden, Nenner Adj_FF_MCap, 70/85/99, Buffer 5 pp (`cmp_buffer_order.py`, `buffer_order.csv`).

| | Cut-off / Liq zuerst (heute) | Cut-off / Label zuerst | Symm. / Liq zuerst | Symm. / Label zuerst |
|---|---|---|---|---|
| Titel Median | 394 | 431 | 348 | 380 |
| Titel Mittel ggue. heute | - | +36,6 | -46,6 | -15,5 |
| Turnover Mittel | 14,0 | 15,0 | 9,4 | 10,1 |
| Turnover in % | 3,55 % | 3,47 % | 2,70 % | 2,65 % |
| Turnover Summe (47) | 658 | 703 | 442 | 474 |
| vom Buffer gehalten | 71 | 79 | 77 | 82 |
| Standard-Coverage | 87,28 % | 88,55 % | 84,14 % | 86,02 % |
| MSCI Treffer | 343 | 360 | 315 | 334 |
| Gew. Overlap | 97,54 % | 98,27 % | 95,53 % | 96,69 % |

BEFUNDE:
- DIE ACHSEN SIND SAUBER GETRENNT und wirken gegenlaeufig. Reihenfolge: +17 Treffer beim
  Cut-off-Buffer, +19 beim symmetrischen, also unabhaengig vom Buffer. Buffer: -28 Treffer bei
  Liq zuerst, -26 bei Label zuerst, also unabhaengig von der Reihenfolge.
- DIE BUFFER-ACHSE IST DER STAERKERE HEBEL: 2,01 Prozentpunkte gew. Overlap gegen 0,73 bei der
  Reihenfolge. Und sie zieht in die falsche Richtung (symmetrisch = schlechterer Match).
- ECHTER TRADE-OFF: symmetrisch senkt den Turnover um rund ein Drittel (658 -> 442 Wechsel,
  relativ 3,55 -> 2,70 %), kostet aber 28 MSCI-Titel und 2 Prozentpunkte Overlap.
- Symmetrisch liegt in 47/48 Perioden UNTER dem heutigen Stand, im Mittel 46,6 Titel tiefer.
  Symmetrisch + Label zuerst in 44/48 Perioden darunter.
- Standard-Coverage symmetrisch/Liq zuerst faellt auf 84,14 %, also unter die 85er-Linie.
- EINORDNUNG DER ENTSCHEIDUNG VOM 29.08.2026 ("Aufstieg am Cut-off"): fuer Helvetica war sie zum
  Stichtag wirkungslos, fuer den Europa-Pool ist sie es NICHT (46,6 Titel im Mittel). Sie fiel auf
  die Seite, die MSCI naeher kommt. Fuer die NaroIX-Serie also deutlich folgenreicher als gedacht.

Messung 7 (2026-09-05), Mid/Small-Haltekante 92 statt 90, Europe Pooled, 48 Perioden
(`cmp_bw92.py`, `bw92.csv`). Wichtig: `_size_segment_entry` hat ZWEI Bandbreiten (bw, bw_ms),
`_size_segment` nur EINE. Ein reines 75/92 geht deshalb nur im Cut-off-Ast; symmetrisch bedeutet
"Mid bis 92" zwangslaeufig bw=7, also auch Large bis 77 und Small-Aufstieg erst unter 78 statt 80.

| | Cut-off 75/90 + Label | Cut-off 75/92 + Label | Symm. bw7 + Label | Symm. bw7 + Liq |
|---|---|---|---|---|
| Titel Median | 431 | 461 | 385 | 350 |
| Turnover Mittel | 15,0 | 13,4 | 8,7 | 7,8 |
| Turnover in % | 3,47 % | 2,90 % | 2,26 % | 2,22 % |
| Turnover max | 27 | 22 | 25 | 24 |
| Standard-Coverage | 88,55 % | 89,08 % | 85,26 % | 83,39 % |
| MSCI Treffer | 360 | 382 | 346 | 326 |
| uns fehlend | 36 | 14 | 50 | 70 |
| Gew. Overlap | 98,27 % | 99,13 % | 97,06 % | 95,97 % |

BEFUNDE:
- 75/92 MIT LABELING ZUERST IST DIE BESTE VARIANTE IM GANZEN VERGLEICH. Sie verbessert alle drei
  Achsen gleichzeitig: mehr Titel (461 vs 431), WENIGER Turnover (2,90 % vs 3,47 %, max 22 vs 27)
  und besserer Match (382 vs 360 Treffer, 99,13 % vs 98,27 %).
- SIE SCHLAEGT AUCH VARIANTE D (FTSE-Nachbau): 382 vs 376 Treffer, 14 vs 20 Fehlstellen,
  99,13 % vs 99,01 %, bei geringerem Turnover. Ohne Total-MCap-Nenner, ohne veraenderte Schwellen,
  ohne den ungeklaerten 2018-Bruch.
- SIE BRAUCHT KEINE CODEAENDERUNG: Toggle "Labeling vor Liquiditaet" an, Feld "Mid/Small Buffer pp"
  auf 7. Beides vorhandene Sidebar-Elemente.
- Kalibrierungsanker: FTSE faehrt auf 68/86-Basis Austritt bei 72/92, also Baender 4 und 6 pp.
  Unsere 5 und 7 auf 70/85 sind dieselbe Kalibrierung.
- ERWARTUNG WIDERLEGT: beim symmetrischen Ast war ein schlechterer Match erwartet worden (haerterer
  Aufstieg, Small erst unter 78). Tatsaechlich verbessert bw=7 den Match ebenfalls: 346 statt 334
  bzw. 326 statt 315 Treffer. Der Halteeffekt oben ueberwiegt den haerteren Aufstieg unten.
- ALLGEMEINE LESART: breitere Haltebaender sind auf diesen Daten auf ALLEN Achsen besser. Die
  Bandbreite gehoert bewusst kalibriert, nicht auf dem Default belassen. Ohne externen Anker (FTSE
  4/6 pp) wird daraus schnell eine Anpassung an den Backtest.

EMPFEHLUNGSSTAND: Cut-off (Aufstieg am Cut-off) + label_before_liquidity=True + Mid/Small-Bandbreite
7 pp. Ohne Code umsetzbar. Offen bleibt die Wirkung auf GM/DM (Schalter ist global) und die
Absicherung des Matches ueber die Historie (nur ein MSCI-Stand vorhanden).

Messung 8 (2026-09-05), Schwellen-Raster: Aufnahme 85 vs 87 mal drei Haltekanten, alles
Cut-off + Label zuerst, Europe Pooled, 48 Perioden (`cmp_grid6.py`, `grid6.csv`).

| | A 70/85 75/90 | B 70/85 75/92 | C 70/85 77/92 | D 70/87 75/90 | E 70/87 75/92 | F 70/87 77/92 |
|---|---|---|---|---|---|---|
| Titel Median | 431 | 461 | 461 | 458 | 493 | 493 |
| Turnover Mittel | 15,0 | 13,4 | 13,4 | 19,1 | 16,3 | 16,3 |
| Turnover in % | 3,47 | 2,90 | 2,90 | 4,16 | 3,31 | 3,31 |
| Turnover max | 27 | 22 | 22 | 34 | 34 | 34 |
| Standard-Coverage | 88,55 | 89,08 | 89,08 | 89,81 | 90,48 | 90,48 |
| MSCI Treffer | 360 | 382 | 382 | 366 | 386 | 386 |
| uns fehlend | 36 | 14 | 14 | 30 | 10 | 10 |
| nicht in MSCI | 34 | 47 | 47 | 43 | 60 | 60 |
| Gew. Overlap | 98,27 | 99,13 | 99,13 | 98,56 | 99,33 | 99,33 |

BEFUNDE:
- REPRODUZIERBARKEIT BESTAETIGT: A und B liefern exakt die Werte aus Messung 6/7 (431/360/98,27
  bzw. 461/382/99,13). Die Pfadabhaengigkeit ist damit stabil.
- B == C UND E == F auf jeder Kennzahl (nur "vom Buffer gehalten" unterscheidet sich). Grund: NUR
  die Mid/Small-Kante entscheidet ueber die Index-Zugehoerigkeit, die Large/Mid-Kante verteilt
  zwischen zwei Segmenten, die BEIDE im Standard liegen. Die Wahl 75 vs 77 ist fuer NX-EU-LM
  folgenlos und zaehlt erst fuer separat publizierte Large-/Mid-Sub-Indizes.
- E HAT DEN BESTEN MATCH (386 Treffer, 99,33 %), IST ABER NICHT DIE BESTE WAHL: der Schritt von B
  auf E bringt nur +4 Treffer und +0,20 pp, kostet aber +13 Nicht-MSCI-Titel, +32 Titel insgesamt
  und Turnover von 2,90 auf 3,31 %. Entscheidend: Coverage 90,48 % liegt OBERHALB von MSCIs
  Zielband 85 +/- 5. Ein Index ueber 90 % Coverage ist methodisch kein 85-%-Index mehr.
- D IST DIE SCHLECHTESTE DER SECHS: Aufnahme 87 laesst das Halteband auf 3 pp schrumpfen,
  Ergebnis 19,1 Wechsel/Periode (4,16 %), schlimmste Periode 34. Mehr Titel als A bei deutlich
  mehr Turnover.

EMPFEHLUNG UNVERAENDERT: B = Aufnahme 70/85, Halten 75/92, Labeling zuerst. Bester Kompromiss aus
Match, Turnover und Coverage; dokumentierte Schwellen 70/85 bleiben; ohne Codeaenderung.

Messung 9 (2026-09-05), Mechanik-Raster Cut-off vs Symmetrisch, alle mit Label zuerst,
Europe Pooled, 48 Perioden (`cmp_grid6b.py`, `grid6b.csv`).

| | A1 | B1 | C1 | D1 | E1 | F1 |
|---|---|---|---|---|---|---|
| Mechanik | Cut-off | Cut-off | Cut-off | Symm. | Symm. | Symm. |
| Aufnahme | 70/85 | 70/85 | 70/87 | 70/85 | 70/85 | 70/87 |
| Aufstieg ab | 70/85 | 70/85 | 70/87 | 65/80 | 65/78 | 65/82 |
| Halten | 75/90 | 75/92 | 75/92 | 75/90 | 75/92 | 75/92 |
| Im Tool einstellbar | ja | ja | ja | ja | NEIN | ja |
| Titel Median | 431 | 461 | 493 | 380 | 385 | 428 |
| Turnover in % | 3,47 | 2,90 | 3,31 | 2,65 | 2,26 | 2,56 |
| Turnover max | 27 | 22 | 34 | 28 | 25 | 26 |
| Standard-Coverage | 88,55 | 89,08 | 90,48 | 86,02 | 85,26 | 87,82 |
| MSCI Treffer | 360 | 382 | 386 | 334 | 346 | 367 |
| uns fehlend | 36 | 14 | 10 | 62 | 50 | 29 |
| nicht in MSCI | 34 | 47 | 60 | 31 | 34 | 38 |
| Abweichung gesamt | 70 | 61 | 70 | 93 | 84 | 67 |
| Gew. Overlap | 98,27 | 99,13 | 99,33 | 96,69 | 97,06 | 98,38 |

BEFUNDE:
- A1 IST DOMINIERT UND SCHEIDET AUS. F1 ist auf JEDER Kennzahl besser (367 vs 360 Treffer,
  98,38 vs 98,27 % Overlap, 2,56 vs 3,47 % Turnover, 67 vs 70 Abweichung, Coverage 87,82 vs 88,55).
  B1 schlaegt A1 ebenfalls auf allem ausser der Zahl der Nicht-MSCI-Titel. Das entkraeftet das
  Argument "A1 sitzt auf den Standard-Leveln": es gibt zwei Varianten, die es komplett schlagen.
- AUSWAHL REDUZIERT SICH AUF DREI:
  B1 = kleinste Gesamtabweichung (61), bester Match im Coverage-Zielband, Aufnahme auf Standard,
       Mechanik gemaess Entscheidung 29.08., Haltekante nach FTSE, ohne Code.
  F1 = Turnover-Alternative (2,56 %) mit noch brauchbarem Match (367 / 98,38 %), aber ZWEI
       Framework-Abweichungen: Aufnahme 87 verlaesst den Marktstandard UND es kehrt die
       Entscheidung vom 29.08. fuer "Aufstieg am Cut-off" um.
  C1 = bester Match ueberhaupt (99,33 %), reisst aber mit 90,48 % die Coverage-Bandobergrenze und
       faellt bei der Gesamtabweichung auf A1-Niveau zurueck (60 Nicht-MSCI-Titel).
- E1 IST IM TOOL NICHT EINSTELLBAR: symmetrisch mit 70/85 und Halten 75/92 braucht zwei
  Bandbreiten (5 und 7), `_size_segment` hat nur eine. Per lokalem Override gerechnet, Repo-Datei
  unangetastet. Override als verhaltensneutral nachgewiesen: D1 durch dieselbe Funktion mit
  gleicher Bandbreite reproduziert Messung 6 exakt (Median 380, 334 Treffer).
- F1 braucht KEINEN Override: Aufnahme 87 plus Bandbreite 5 ergibt rechnerisch genau 75 / 92.
- Korrektur zu einer Vorab-Aussage: die Bestandsbenachteiligung im symmetrischen Ast ist bei F1
  NICHT kleiner als bei D1. Beide haben 5 pp Abstand zwischen Aufstiegs- und Aufnahmeschwelle
  (F1: 82 vs 87, D1: 80 vs 85). Nur E1 ist mit 7 pp schlechter.

EMPFEHLUNG UNVERAENDERT: B1 (= B aus Messung 8). Alternative mit Turnover-Prioritaet: F1, aber
dann bewusst mit zwei Framework-Abweichungen.

FIF-Luecke geklaert (2026-09-07, `chk_fif.py`). Bisher als offene Luecke gefuehrt: uns fehlt
MSCIs Mindest-FIF von 0,15 und der Foreign-Room-Screen. Status jetzt: BEWUSSTE ABWEICHUNG,
keine Baustelle.

Gemessen 19.08.2026 auf 9.391 investierbaren Zeilen:
- 2.371 Titel haben ueberhaupt IF < 1
- 1.515 haetten FIF < 0,15 und wuerden bei MSCI ausscheiden, Gewicht 0,55 % des Adj_FF
- davon 1.477 CHINA, nur 38 ausserhalb, davon 15 DM

URSACHE UND WARNUNG: unser `IF` vermischt zwei Dinge, die MSCI getrennt haelt. Der China-Zweig in
`apply_fol_matrix` ueberschreibt den FOL-Wert und setzt IF = china_if = 0,20. Damit gilt
FIF = FF% x 0,20 < 0,15 fuer jeden chinesischen Titel mit unter 75 % Streubesitz, also fast alle.
Bei MSCI ist der FIF Streubesitz-mal-FOL, die stufenweise China-A-Teilaufnahme ist ein SEPARATER
Mechanismus (eigener Anhang, "third step of weight increase") und unterliegt dem 0,15er-Boden
erkennbar nicht. WER DEN SCREEN EINBAUT, MUSS DEN IF VORHER IN ZWEI FAKTOREN ZERLEGEN:
FOL-Faktor (dort gehoert die Grenze hin) und China-Teilaufnahmefaktor (dort nicht).

Ausserhalb Chinas ist die Luecke faktisch bedeutungslos: 38 Titel, die groessten davon Southern
Copper (FF 11 %, kein FOL), Zijin Gold HK (13,5 %), Ecopetrol (11,5 %). Alle scheitern am reinen
Streubesitz, nicht an einer Auslandsbeschraenkung, und alle drei blieben bei MSCI ueber die
Ausnahme in 2.3.6.1 drin (FIF < 0,15 zulaessig, wenn Float-MCap >= 1,8x der Mindestanforderung).

Bestaetigt zugleich: die FOL-Anwendung sitzt bei uns an der richtigen Stelle. Berechnung im
Universum, Kumulation und Segmentierung auf Adj_FF, Gewichtung auf Adj_FF. Das entspricht fuenf
von sechs Anbietern; nur der Ausschluss-Screen fehlt. Der Sidebar-Radio steht korrekt auf
"Selektion"; "Gewichtung" waere der Fehler (IF erst am Ende), und die App markiert das selbst.

Was an D NICHT FTSE ist (Grenzen des Nachbaus): Segment weiter auf Wertpapier- statt Firmenebene,
keine 10-%-Kappung des Regionaluniversums (7.3.4), keine absoluten Boeden 150/30 Mio USD.
Ausserdem ist `if_cum_col = Total MCap` in der Sidebar nicht waehlbar, D braucht eine Codeaenderung.
Nebenwirkung von Total MCap: die Segmentierung nutzt gar keinen Float mehr, ein Gigant mit winzigem
Float waere Large Cap und fiele erst am 10-%-Free-Float-Gate raus. FTSE faengt das mit dem
5-%-Float-Screen plus Investability-Gewichtung ab, wir haetten dort keinen Groessen-Waiver.

Skript: `cmp_ftse_variant.py` im Scratchpad.

Noch zu messen, bevor entschieden wird:
1. ERLEDIGT (Messung 3): Turnover und die FTSE-Variante.
2. OFFEN: was B bzw. D bei NX-GM-LM und NX-DM-LM anrichtet, mangels Benchmark ersatzweise ueber
   Turnover und Coverage-Kennzahlen.
3. OFFEN: Sensitivitaet auf `size_buffer_pp_ms` (5 vs 7) sauber durchmessen, siehe Warnung oben.
4. OFFEN falls D verfolgt wird: Segment auf Firmenebene, sonst ist es FTSE-Logik auf der
   falschen Aggregationsebene.

Skripte: `cmp_label_order.py` und `cmp_pooled_msci.py` im Scratchpad dieser Session.

Nebenbefund aus dem Regelwerksabgleich, betrifft bestehende Doku:
- Unsere Kumulationsbasis ist Marktstandard, nicht Sonderweg. MSCI (FIF), Solactive (Final
  Weighting Factor), Morningstar, STOXX und Bloomberg kumulieren alle min(Float, FOL), was
  algebraisch unser `FF% x IF` ist. Nur FTSE nimmt volle MCap.
- Die Laender-Mindestbesetzung im Europe-Pooling ist KEINE Eigenkonstruktion, wie es in
  `MULTI_PERIOD.md` und im Code-Kommentar steht. Bloomberg (min. 3 Standard-Titel je Land,
  aufgefuellt aus Small/Micro) und STOXX (min. 5 DM / 3 EM je Land, Bestand x1,5) fahren sie
  je Land. MSCI fuehrt sie je Markt. Kommentar und Guideline sind noch nicht nachgezogen.
- Luecken ohne Gegenstueck im Standard: keine Handelsfrequenz-Pruefung, keine Mindesthistorie,
  kein Groessen-Waiver auf den Mindest-Free-Float (alle sechs haben einen).

## Tool-Aufraeumen Segmentgrenzen (2026-09-07, NICHT committet)

Acht Aenderungen, alle bei ihren Defaults verhaltensneutral. Regressionssuite 277 -> 312 Tests,
0 Fehler. Ruff F821/F811 sauber. AppTest laeuft ohne Exception (kommt ohne Master-File nur bis
`st.stop()`, der Sidebar-Block ist damit nicht end-to-end geprueft).

UMGESETZT
1. `segment_edges()` in `pipeline_core.py`: EINE Quelle fuer alle Segmentkanten aus
   (Schwellen, drei Bandbreiten, Variante, Buffer an/aus). Rueckgabe thresholds/rise/hold/bands/rows.
   Vier neue Tests sperren sie gegen `_size_segment`, `_size_segment_asym`, `_size_segment_entry`.
2. `eumss_coverage` als eigener Pipeline-Parameter, Default None = small_thr, also identisch zu
   frueher. Damit ist Small-Kante 98 mit Boden-Kalibrierung 99 moeglich, ohne den Boden
   mitzuschleppen (frueher zwangslaeufig 759 -> 1.574 Mio USD). Sidebar-Feld "Kalibrierpunkt (%)"
   unter der neuen Gruppe "Groessenboden (EUMSS)", an allen 5 Aufrufstellen durchgereicht.
   Rueckgabe enthaelt jetzt `eumss_coverage_used`.
3. Schwellenfelder von `int()` auf `float()`, Komma erlaubt. Frueher fiel "99,5" STILL auf 99
   zurueck. Jetzt sichtbare Warnung bei unlesbarer Eingabe plus Plausibilitaetspruefung
   (aufsteigend, <= 100) und ein Hinweis, dass 100 kein sinnvoller Kalibrierpunkt ist.
4. Buffer-Block umgebaut: 179 Zeilen raus, 96 rein. Drei Bandbreitenfelder mit echten Defaults
   5 / 5 / 0,5 statt Feld + Platzhalterfeld + Checkbox. `0 = aus`, damit ersetzt die dritte
   Bandbreite die fruehere Small-Cut-Checkbox. Drei Prosa-Captions und der eingeklappte Expander
   sind durch EINE sichtbare Tabelle aus `segment_edges()` ersetzt. Radio hat jetzt `captions=`
   je Variante; der ueber 48 Perioden verifizierte Befund "Asym == Cut-off fuer Large+Mid" steht
   im Gruppen-Hilfetext, damit er beim Umbau nicht verloren geht.
5. Kriterienbox: Segmenttabelle unter der Box, EUMSS-Zeile zeigt Kalibrierpunkt, FF-Ratio und den
   tatsaechlichen Boden in Mio USD (aus `st.session_state["_last_eumss_full"]`, also dem letzten
   Lauf). Helvetica- und Serie-Zweig nutzen jetzt dieselbe Tabelle.
6. Settings-Blatt: statt "Small-Cap Coverage-Cut 99/99,5" jetzt drei Bandbreiten einzeln, der
   EUMSS-Kalibrierpunkt und vier Zeilen "Segmentgrenzen" mit Aufnahme / Aufstieg / Verbleib je
   Segment. Bisher protokollierte das Blatt bei abweichender Small-Schwelle FALSCHE Werte.
7. Hartkodierte 99 raus. Verblieben sind drei reine Kommentare (zwei davon bei den
   Total-Markets-Aufrufen), keine benutzersichtbare Stelle mehr.

NICHT ANGEFASST
- Methodik: `label_before_liquidity`, Bandbreiten-Werte, Aufnahmeschwellen. Alles Entscheidungen,
  keine Fixes.
- Total MCap als Kumulationsbasis: bleibt blockiert bis der +890-Titel-Sprung am 2018-08-15 erklaert
  ist.
- Regel zur Listing-Wahl, Mindest-FIF, Handelsfrequenz, Mindesthistorie, Kontinuitaetsregel:
  dokumentierte Abweichungen ohne gemessenen Schaden.

OFFEN
- Der Sidebar-Block ist nur statisch geprueft (Syntax, Ruff, Unit-Tests der Logik). Ein Lauf mit
  Master-File fehlt, weil AppTest ohne Upload an `st.stop()` endet.
- Migration: wer `apply_small_buffer` frueher abgewaehlt hatte, muss die dritte Bandbreite auf 0
  setzen. Der alte Checkbox-Key `apply_small_buffer` existiert nicht mehr als Widget.
- Mit `float()` wirken Dezimaleingaben, die vorher still verworfen wurden.
- Nichts davon ist committet, der Arbeitsbaum enthaelt weiterhin auch die aelteren
  Helvetica-Guideline-Aenderungen.

## Offene Punkte

- Aenderung ist noch nicht committet (Code, Docs, progress.md).
- Nur informativ: die Zeilenangaben in `PIPELINE_IST.md` (z.B. `pipeline_core.py:689` fuer
  `apply_universe_exclusions`, real 731) sind gegenueber dem aktuellen Arbeitsstand alle
  veraltet, weil noch weitere uncommittete Aenderungen im File liegen. Nicht angefasst.

## Doku-Stand

Alle 10 Fundstellen des NAICS-Ausschlusses in `Claude_Guideline_Drafts/` wurden am 2026-08-23
angepasst: Regel entfernt, dazu jeweils eine datierte Notiz mit Begruendung. Betroffen:
`PIPELINE_IST.md`, `SELECTION.md`, `HANDOVER.md`, `Helvetica_Selektionskriterien.md`,
`Helvetica_Selektionsprozess_Automatisierung.md`, `Helvetica_Selection_Tool_Spec.md`
(Regeltabelle 6-9 auf 6-8 umnummeriert, Querverweis "Zu Regel 8" auf 7 gezogen, NAICS-Feld in
der Feldtabelle auf "nur Info" gesetzt), `NaroIX_Europe_Global_Index_Guideline.md`,
`NaroIX_Helvetica_Index_Guideline.md`. `NAICS` bleibt als Master-Spalte in
`MASTER_STATIC_REQUIRED` und in der Feldliste von HANDOVER.md.

## Master-File 08/2026 (Pruefung 2026-08-24)

`NaroIX_Universe_Selection_Master_Final_08_2026_Complete.xlsx` (59.516 Zeilen, 458 Spalten,
Sheets `Master` + `Manuell Added`) laeuft vollstaendig durch die Pipeline: 48 Perioden erkannt
(2014-11-19 bis 2026-08-19), alle dynamischen Prefixe bekannt, `MASTER_STATIC_REQUIRED`
komplett, `Mapping Country` ohne Leerwerte und alle 48 Laender in der Historical
Classification, keine Exchange-Ticker-Dubletten. Alle 25 Produkte der Index Series bauen zum
2026-08-19 mit Gewichtssumme exakt 100. Neue Spalte ist `Country of GeoRev` (laeuft als
`extra_static_col` mit, wird von keiner Regel genutzt).

Wichtig: es ist kein reiner Spalten-Zuwachs, sondern ein neuer FactSet-Zug. Gegen
`Old Files/..._v3_ohne01012025_FESTWERTE.xlsx`: 12.357 Keys neu, 5.605 weg, revidierte
Historienwerte in allen 47 gemeinsamen Perioden, `Country Mapping` bei 884 gemeinsamen Titeln
geaendert. Auf identischer Periode 2026-05-20 ergibt das 4,3 % Turnover in NX-GM-LM und 5,0 %
in NX-EU-LM. Backtests aus Juli sind mit dem neuen File nicht reproduzierbar.

Master-Name ab jetzt: `NaroIX_Universe_Selection_Master_Final_08_2026_Complete.xlsx`.

Stand der Pruefungs-Punkte:

- ERLEDIGT 2026-08-24: Master-Glob in `tests/test_regression.py` auf
  `*Selection_Master*.xlsx` (ohne Helvetica) umgestellt. Deckt den neuen Namen
  `NaroIX_Universe_Selection_Master_Final_08_2026_Complete.xlsx` und die alten ACWI-Staende ab,
  die Integrationstests laufen wieder statt still zu skippen.
- ERLEDIGT 2026-08-24: `Historical Classification.xlsx` nachgezogen. Spalte `2014-11-19` ist
  wieder da (48 Laender x 49 Datumsspalten), Legacy-Spalte `2015-01-01` bleibt bewusst weg.
  NaN-Muster plausibel: CZECH REPUBLIC erst ab 2019-02-20 als EM, RUSSIA ab 2022-02-16 raus.
  Verifiziert: 2014-11-19 laeuft wieder voll durch (Universe 22.898, IMI 5.810, EU-LM 297,
  GM-LM 1.950), die Reihe waechst monoton bis 2015-08-19.
  Rest-Schiefstand ohne Wirkung: `Selection Dates.xlsx` fuehrt noch 2015-01-01 (kein
  Master-Spaltensatz dazu), die HC hat mit 2026-11-18 bereits die naechste Periode vor.
- ERLEDIGT 2026-08-24: `China Inclusion Factor.xlsx` nachgezogen, 49 Zeilen deckungsgleich mit
  den Selection Dates, keine Luecke, Hardcode-Fallback 0,20 greift nirgends mehr.
- ERLEDIGT 2026-08-24: `Country_Classification.xlsx` nachgezogen. IRELAND hat `Europe = YES`
  wieder, CZECH REPUBLIC und TURKEY neu auf YES, MOROCCO raus / PERU rein, DM/EM deckungsgleich
  mit der letzten HC-Spalte. Rest-Differenz nur latent: TURKEY steht im File als Europe, fehlt
  aber in `EUROPE_COUNTRIES` (`pipeline_core.py`). ERLEDIGT: TURKEY ist aufgenommen, die
  Code-Liste ist jetzt deckungsgleich mit der Spalte `Europe` im File (20 zu 20, keine
  Differenz). Die Liste ist rein geografisch, die DM/EM-Trennung macht jede Verwendung selbst
  ueber `Classification == "DM"`. A/B geprueft (2026-08-19, 2024-08-21, 2016-08-17, zusaetzlich
  europe_pool=True): 0 Differenz in NX-EU-LM / NX-EU-T / NX-EU-T30 und 0 Segmentwechsel, weil
  Tuerkei in allen 49 Perioden EM ist.

## Coverage-Treppe im Investable-Universe-Export (2026-08-24)

Das Sheet "Investable Universe" (Detail-Download im Multi-Period-Tab und im Europe-MP-Tab)
zeigt jetzt direkt nach `Index_Weight` zwei neue Spalten:

- `Coverage_before_%` (bisher `_c_before`, nur das Exportlabel ist neu): Coverage VOR dem
  Titel, das ist der Wert, den die Segmentregel testet. Steht jetzt bei seinen zwei Geschwistern
  statt weiter vorne im Sheet.
- `Cum_FF_MCap`: kumulierte Coverage-Basis je Segmentierungsmarkt, in Waterfall-Reihenfolge
  (Sortierung Total MCap absteigend), inklusive der eigenen Zeile.
- `Coverage_after_%`: dieselbe Treppe als Prozent des Markt-Totals.

Berechnet werden sie in `run_selection_pipeline` direkt neben `_c_before`, also aus derselben
Groupby-Schleife wie die Segmentierung selbst. Damit gibt es keine zweite Implementierung der
Coverage-Logik, und die Spalten stimmen in jedem Modus (Europe-Pooling, MSCI Logic, Buffer).
Rein informativ, keine Regel haengt daran.

Lesart: es gilt `Coverage_before_%(Zeile n+1) = Coverage_after_%(Zeile n)`, der Cut liegt also
genau zwischen den beiden Zeilen, wo `Coverage_after_%` die Schwelle (70 / 85 / 99) reisst. Der
Nenner ist rekonstruierbar als `Cum_FF_MCap / Coverage_after_% * 100`. Dieselbe Treppe steht
jetzt auch in der Helvetica-Pipeline (`build_helvetica_pipeline`), damit beide Pipelines
dieselben Spalten fuehren.

Verifiziert am 2026-08-19 ueber alle 47 Segmentierungsmaerkte: Treppe monoton, Verkettung
`Coverage_before_%(n+1) == Coverage_after_%(n)` exakt, Endwert je Markt exakt 100 %, Segmentgrenzen
sauber auf 70 / 85 (Large max 69,994 / Mid 70,054 bis 85,000 / Small ab 85,004). Sieben neue
Regressionstests decken diese Eigenschaften ab, Suite jetzt 145 PASS / 0 FAIL / 0 SKIP.

Nebenbei gefunden: der Master-Glob der Tests hat die Office-Sperrdatei
`~$NaroIX_Universe_Selection_Master_...xlsx` mitgenommen (entsteht, sobald der Master in Excel
offen ist, ist per mtime die neueste und nicht lesbar). Die Integrationstests sind dadurch
still weggeskippt. Jetzt werden `~$`-Dateien gefiltert und die Kandidatenliste wird
durchprobiert, bis ein lesbarer Master gefunden ist.

## Konsistenz-Nacharbeiten (2026-08-24)

- `Index_Reason`: Label `Coverage-Cut (< 85 %)` heisst jetzt `Coverage-Regel (< 85 %)`. Der
  Titel ist INNERHALB des Cut-offs und damit ueber die regulaere Regel drin, das alte Wort
  las sich wie "weggeschnitten".
- HANDOVER.md §4 auf den 08/2026-Master gezogen: 59.516 Zeilen statt 52.764, Dateiname genannt,
  Notiz zum Sheet "Manuell Added", Spaltenliste S bis Z auf die tatsaechliche Reihenfolge
  korrigiert (`Country of GeoRev` an Position V, das ist die Spalte, die dort vorher als
  `Country of Rev_Risk` dokumentiert war; `Country Mapping` ist auf X gewandert, der Loader
  loest ueber den Namen auf), letztes Selection Date 2026-08-19, und die falsche Zeile
  "`pipeline_core.py` does not exist" berichtigt.
- Suite nach allen Aenderungen: 145 PASS / 0 FAIL / 0 SKIP.

## Float-Datenlücke als Erklärung für die EU-Fehlliste: ausgeschlossen (2026-08-24)

Frage: liefert FactSet fuer viele europaeische Titel keinen Free Float, wird dadurch der
gepoolte Coverage-Nenner zu klein und rutschen MSCI-Europe-Mitglieder bei uns in Small Cap?

Gemessen am Stichtag 2026-08-19, Europe Pooled, gegen die 52 Ticker aus dem
Investable-Universe-Sheet:

- Die Luecke ist in der ANZAHL gross: Polen 80,5 % der Primaries ohne Float, Spanien 51,9,
  Frankreich 44,9, Italien 42,7, Schweden 36,8, Daenemark 33,1, Belgien 32,6, Finnland 31,0,
  Deutschland 29,1, Norwegen 23,8; dagegen Schweiz 6,9 und UK 5,1.
- In MCAP sind es Kruemel: diese Titel tragen 0,1 bis 4,4 % der Landes-MCap.
- Nenner-Effekt: 1.947 DM-Europa-Titel ohne Float, 0,146 Bio USD Total MCap, mit Median-FF%
  0,087 Bio USD Float auf 16,34 Bio USD Nenner = +0,53 %.
- Gegenlauf mit imputiertem Float (Landes-Median-FF%, 16.486 Titel weltweit): Nenner 16,340 zu
  16,419 Bio, Pool DM-Europa 1.065 zu 1.091, EU L+M 299 zu 302, und 0 von 52 wechseln das
  Segment. Coverage-Verschiebung Median 0,09 pp, die knappsten Titel (Var Energi 86,12,
  Delivery Hero 86,17) brauchen 1,1 pp.
- Nur 26 der 1.947 ergaenzten Titel kommen ueberhaupt in den Pool, der Rest scheitert danach am
  EUMSS-Floor oder an der Liquiditaet. Fehlender Float ist bei diesen Namen Symptom der Groesse,
  nicht Ursache des Fehlens.
- Harte Obergrenze: der gepoolte Nenner enthaelt bereits 97,9 % des gemeldeten Free Floats
  aller 5.583 DM-Europa-Primaries (16,340 von 16,692 Bio USD). Alles ungefiltert im Nenner
  waeren +2,15 %, also 90 % Coverage auf 88,1 %. Das holt 3 bis 4 der 52.

Ursache bleibt der gepoolte Cutoff (eine Linie bei ~9,3 Mrd statt 16 Laenderlinien zwischen
4,73 und 23,04 Mrd) plus die fehlende GMSR-Klammer gegenueber MSCI. Von den 52 waren 34 in
frueheren Perioden im Index (Sodexo 42 von 48 Perioden, Evonik 34, Alstom 30, Stora Enso 29),
18 waren nie drin. Buffer-Variante ist irrelevant: "Aufstieg am Cut-off" und "Symmetrisch"
liefern fuer diese 52 in jeder Periode identische Index-Zahlen.

## Master-Update 2026-08-24 14:34: 359 manuelle Float-Werte

Der Master wurde erneut ersetzt (180,57 MB, Master-Sheet 59.545 Datenzeilen, +29). Struktur
unveraendert: Loader ohne Fehler, 48 Perioden, 26 statische Spalten in identischer Reihenfolge,
alle Pflichtspalten, gleiche 9 Feld-Prefixe, gleiche Warnung (14 auffaellige ISIN-Gruppen).
Regression danach: 145 PASS / 0 FAIL / 0 SKIP.

Das Sheet "Manuell Added" ist von 4 auf 359 Eintraege gewachsen und hat jetzt eine Spalte
`Float %`. Alle 359 Ticker sind im Master-Sheet vorhanden.

OFFENER PUNKT: die Float-Werte stecken nur in der Periode 2026-08-19 (359 von 359 mit FF% > 0).
Vorperioden: 2026-05-20 nur 11, 2026-02-18 nur 17, 2020-05-20 118, 2014-11-19 96. Im
Multi-Period-Lauf springt das Universe damit an der letzten Umstellung um 322 Titel und die
Namen erscheinen dort als Zugaenge, also Turnover aus einer Datenaenderung statt aus dem Markt.
Wenn die Werte historisch gelten sollen, muss `Float MCap = Total MCap x Float %` je Periode
zurueckgeschrieben werden. Nebenbefund fuer eine FactSet-Rueckfrage: fuer diese Namen liefert
FactSet 2014 und 2020 mehr Float als 2026, die Abdeckung hat sich verschlechtert.

Wirkung auf 2026-08-19 (je Land): gm_complete 27.966 auf 28.288, Large/Mid/Small 1.011/1.231/
6.048 auf 1.020/1.237/6.108, IMI 8.290 auf 8.365, NX-EU-LM 339 auf 343, NX-GM-LM 2.242 auf
2.257, alle 25 Produkte mit Gewichtssumme exakt 100.

Europe Pooled: Pool DM-Europa 1.065 auf 1.076, EU L+M 299 auf 302, Nenner 16,340 auf 16,379 Bio
USD (+0,24 %), Titel ohne Float 1.947 auf 1.706 und deren MCap 0,146 auf 0,052 Bio. Die 52
Ticker der Fehlliste bleiben ALLE Small Cap, Coverage-Median 90,56 auf 90,45. Damit ist der
Float-Befund oben mit echten Werten bestaetigt, nicht nur mit imputierten.

## Free-Float-Waiver: Ankervergleich (2026-09-08, gemessen)

Anlass: Vorschlag, die 10-%-Mindest-Free-Float-Huerde fuer Titel ueber 10 Mrd USD Total MCap
entfallen zu lassen, analog zum Solactive-Konzept. Gemessen am 19.08.2026, Boden 759 Mio USD,
Skript `chk_waiver_anchors.py`. Gewaivert wird NUR das FF-%-Bein, die beiden Groessenbeine
(Total >= Boden, Float >= halber Boden) und der Liquiditaetsscreen bleiben UND-verknuepft.

| Anker | Kandidaten | davon liquide |
|---|---|---|
| MSCI-Stil: Float >= 1,8 x Boden (1.366 Mio) | 11 | 11 |
| Solactive: Float >= 1,0 Mrd | 14 | 11 |
| Vorschlag: Total >= 10 Mrd | 21 | 15 |
| STOXX-Stil: Float >= 1,8 x halbem Boden (683 Mio) | 24 | 18 |

BEFUNDE:
- MSCI-Stil und Solactive treffen dieselben 11 Titel. Der Vorschlag ist auf diesen Daten eine
  echte Obermenge davon (11 + 4), umgekehrt bringt Solactive keinen Titel, den der Vorschlag
  nicht haette.
- Die 4 zusaetzlichen: Hapag-Lloyd (DE, FF 3,6 %, Float 0,93 Mrd, ADTV 2,3 Mio), Chery Automobile
  (CN, 9,7 %, 0,78 Mrd), Kingdom Holding (SA, 4,7 %, 0,56 Mrd), Guangxi Guiguan (CN, 5,5 %,
  0,70 Mrd). Kleinster Float unter dem Vorschlag: 564 Mio USD.
- ANKERFRAGE: alle fuenf Anbieter mit Waiver haengen ihn an den FLOAT, keiner an die Total MCap.
  Solactive absolut (1,0 Mrd neu / 0,75 Mrd Bestand), MSCI relativ (1,8 x Mindestgroesse), STOXX
  relativ (1,8 x halbem Country-Cutoff), Bloomberg ueber ein Laender-Perzentil, FTSE gar nicht
  (dafuer nur 5 % Huerde). Inhaltlich folgerichtig: die Mindest-Float-Regel fragt nach
  handelbaren Stuecken, dazu sagt die Total MCap nichts.
- Ein relativer Float-Anker skaliert mit dem Boden mit und braucht keine Nachkalibrierung.
- VORAUSSETZUNG UNVERAENDERT: kein Waiver ohne Mindesthistorie. SpaceX steckt in allen vier
  Varianten (1 von 48 Perioden im Master, ADTV 16,87 Mrd, 3M = 6M = 12M identisch).

## Bodenbewegung nachgemessen (2026-09-08, `chk_waiver.py`)

Boden 2026-05-20: 664 Mio USD, 2026-08-19: 759 Mio USD, also +14,4 % in einer Periode.
771 Titel liegen zwischen altem und neuem Boden (EM 489, DM 282), davon 409 liquide und
float-gross genug, Adj_FF-Summe 201,4 Mrd USD. Diese 409 fallen allein aus der Bodenbewegung,
nicht weil sie geschrumpft waeren. MSCI (3.1.2.2/3.1.2.3) und STOXX nehmen Bestandstitel von der
Groessenanforderung komplett aus, FTSE faehrt asymmetrisch (150 Mio neu / 30 Mio Bestand),
Bloomberg absolute Boeden, Solactive hat gar keinen separaten Boden. Wir pruefen jeden Titel
jede Periode gegen den frisch gerechneten Boden, ohne Bestandsschutz.

## Handelsfrequenz: nicht im Code (2026-09-08 geprueft)

`grep` ueber `pipeline_core.py` und `naroix_benchmark.py` findet keinen Handelsfrequenz- oder
Nichthandelstage-Screen. Der Check findet laut Fachseite beim Aufsetzen des Index statt (Titel
faellt raus, Gewicht wird proportional verteilt), also am Gewichtungsende und ausserhalb der
Pipeline. Konsequenz: KEINER der Backtests dieser Session bildet ihn ab, das Backtest-Universum
ist entsprechend etwas weiter als das Live-Universum. Alle sechs Anbieter fuehren den Screen in
der SELEKTION (MSCI 90/80 % ueber 3M, STOXX 90/80 neu und 80/70 Bestand, Solactive < 10
Nichthandelstage in 3M, Morningstar < 20 in 6M / 30 Bestand, Bloomberg keine 10 am Stueck, FTSE
eigener Trading Screen).

## Waiver-Anker 2,0 x Boden (2026-09-08, `chk_anchor20_listing.py`)

Gemessen 19.08.2026, Boden 759 Mio USD. Nur das FF-%-Bein wird gewaivert.

| Anker | Schwelle | Kandidaten | liquide |
|---|---|---|---|
| STOXX-Stil 1,8 x halber Boden | 683 Mio | 24 | 18 |
| Solactive 1,0 Mrd absolut | 1.000 Mio | 14 | 11 |
| MSCI-Stil 1,8 x Boden | 1.366 Mio | 11 | 11 |
| ENTSCHEIDUNGSKANDIDAT 2,0 x Boden | 1.518 Mio | 11 | 11 |
| 2,5 x Boden | 1.898 Mio | 10 | 10 |

2,0 x Boden trifft exakt dieselben 11 Titel wie Solactives fester 1-Mrd-Anker und wie MSCIs
1,8-fache Mindestgroesse. Erst bei 2,5 x faellt der erste weg (Shanghai International Port,
1,64 Mrd Float). Zwischen 1,0 und 1,9 Mrd liegt also ein Plateau, der Anker sitzt mittig und
nicht auf einer Kante. Skalierungsargument: der Boden lief ueber die 48 Perioden von 152 bis
759 Mio, ein fester 1-Mrd-Anker waere 2014 das 3,6-fache und heute nur noch das 1,3-fache des
Bodens gewesen.

Die 11 Titel: SpaceX, Saudi Aramco, Adnoc Gas, Itau Unibanco, Huaneng Lancang, Ubiquiti,
Barito Renewables, Christian Dior, TAQA, LIC India, Shanghai International Port.

Bloomberg wortwoertlich nachgelesen (1.2.6): Ausnahme, wenn "the security float market
capitalization is greater than 0.5 times the 70th percentile of its country's cumulative float
market capitalization". Damit haengt der Waiver bei ALLEN FUENF Anbietern am Float, bei keinem
an der Total MCap.

## Bestandsschutz am Boden: MSCI und STOXX machen ZWEI Dinge (2026-09-08)

MSCI 3.1.2.2 und STOXX 3.3.1.2 sind inhaltlich deckungsgleich:
1. RANG-MITNAHME. Der Rang, der den Boden zuletzt definiert hat, wird gemerkt. Liegt seine
   Coverage jetzt zwischen 99 und 99,25 %, bleibt er der Boden. Unter 99 % wird auf die 99er-Kante
   zurueckgesetzt, ueber 99,25 % auf die 99,25er-Kante.
2. BESTANDSAUSNAHME. MSCI: "New companies are evaluated relative to this updated threshold,
   whereas all existing constituents will not be evaluated relative to this investability
   requirement" (gilt auch fuer das 50-%-Float-Bein, 3.1.2.3). STOXX: "Existing components are
   exempt from the updated Full Market Capitalization screen."
FTSE loest es ueber asymmetrische Absolutwerte (150 Mio Aufnahme / 30 Mio Ausschluss, Rule 7.6.2).
Bloomberg ueber feste Boeden (100 Mio DM / 50 Mio EM), da bewegt sich nichts.
SOLACTIVE HAT UNSER PROBLEM NICHT: es gibt gar keinen absoluten Boden. Das Universum entsteht aus
den Screens, danach wird alles in Buckets geteilt (All Cap 0 bis 100 %). Die einzige Groessenkante
ist der Coverage-Cut, und der hat einen Buffer (Small Cap 85 bis 99 %, Top 98,5 / Bottom 99,5).
Unser Problem entsteht daraus, dass wir ZWEI Groessenkanten haben, den absoluten EUMSS-Boden und
den Small/Micro-Coverage-Cut, und nur die zweite eine Hysterese hat.

Messung ueber alle 48 Perioden (`chk_floor_maintenance.py`, `floor_maint.csv`). Proxy-Pool =
Boden + Float-Bein + Liquiditaet, ohne Segmentierung, also Obergrenze fuer den Indexeffekt.
- Boden min 152 / Median 349 / max 759 Mio USD
- Periodenaenderung |%|: Median 4,6, Mittel 10,2, max 125,3
- 7 von 47 Perioden mit ueber 10 % Bodenanstieg
- Datenartefakt: 2019-08-21 faellt der Boden auf 152 Mio (-53,4 %) und springt zur Folgeperiode
  auf 341 (+125,3 %). Genau die Sorte Ausschlag, die die Rang-Mitnahme abfaengt.
- Abgaenge je Periode Median 547, Mittel 602, max 1.844
- Maintenance-Schwelle k x Boden rettet davon: k=0,90 Median 115 (23 %), k=0,85 Median 152 (30 %),
  k=0,75 Median 211 (41 %)

## In-Eligible: Ort und Fuellstand (2026-09-08 geprueft)

Handelsfrequenz und Sanktionen laufen laut Fachseite ueber In-Eligible.xlsx. Zwei Befunde:
- Die Datei enthaelt heute NUR ZWEI BEISPIELZEILEN mit Dummy-ISINs (CNE100000XXX Stock Connect
  Sell-Only, INE000000XXX FOL Breach India). Kein Backtest hat je einen echten Ausschluss
  angewandt.
- Der Filter laeuft in `run_selection_pipeline` als Schritt 7 (pipeline_core.py:2708), also NACH
  der Segmentierung und vor der Gewichtung. Ein in-eligibler Titel steht damit noch im
  Coverage-Nenner und verschiebt die Coverage-Position aller anderen. MSCI und STOXX entfernen ihn
  vor der Segmentierung. Fix: Filter vor den Waterfall ziehen.
Der Mechanismus als solcher ist periodenscharf (From/To je ISIN) und damit backtestfaehig.

## Listing-Spalte bedeutet Gattung, nicht Boerse (2026-09-08, `chk_listing_dupes.py`)

Wichtig fuer die geplante Regel "nur Primary Exchange": die Master-Spalte `Listing` markiert
ueberwiegend ZWEITE GATTUNGEN und NVDR-Linien, nicht Zweitnotierungen.
- Rohsnapshot 19.08.2026: 59.545 Zeilen, davon 2.387 Secondary
- Waterfall-Pool: 9.390 Zeilen, davon 125 Secondary, und NULL davon teilen sich eine ISIN mit
  einer Primary-Zeile im Pool
- Die groessten Secondary-Titel: Alphabet C (1.832 Mrd Adj_FF), Berkshire B (242), Samsung
  Electronics Vorzug (106), Petrobras (70), Delta Electronics Thailand (39), Atlas Copco B,
  Investor A, HEICO A, Roche. Dazu 73 thailaendische NVDR-Linien.
- Ein hartes Primary-only wuerde 125 Titel und 2,27 % des Pool-Adj_FF loeschen und dabei KEINEN
  einzigen Doppeleintrag entfernen.

Echte Mehrfachnotierungen sind fast nicht vorhanden: 59.496 eindeutige ISINs auf 59.545 Zeilen,
nur 49 ISINs doppelt. Davon 34 dieselbe Boerse mit zweiter Handelswaehrung (Temenos CHF/USD an
SIX, Accor EUR/USD Paris, Eiffage, Sirius GBP/EUR London), nur 15 wirklich zwei Boersen. Die
Zweitlinie hat fast immer keinen ADTV-Wert und faellt am Liquiditaetsscreen. Auf Entity-ID-Ebene:
2.183 Firmen mit mehreren Zeilen, davon 2.158 an EINER Boerse (Gattungen) und nur 25 an mehreren.

Die beiden hartkodierten Muster sind heute wirkungslos: HK-Ticker in CNY trifft 1 Zeile,
London-USD-Secondary trifft 0 Zeilen.

Vorbild fuer die Regelformulierung, Solactive 2.1.2 Choice of Listing: liquideste HEIMISCHE
Notierung (min aus 1M und 6M ADTV), sonst liquideste regionale, sonst liquideste auslaendische,
und ein Wechsel zurueck erfordert VIER aufeinanderfolgende Selektionen. MSCI 3.1.2.4 fuehrt die
Prioritaet Local > Foreign same region > Foreign other region. Unser Helvetica-Dedup (Schritt 3b)
hat die Wechsel-Hysterese ausdruecklich NICHT.

### Rang-Mitnahme nachgerechnet (`chk_floor_stability.py`, 48 Perioden)

Heutige Regel (kalt auf 99 %) gegen MSCIs Rang-Mitnahme mit Band 99 bis 99,25:

| Periode | Boden heute | Rang | Boden MSCI-Regel | Rang | zusaetzlich im Universum |
|---|---|---|---|---|---|
| 2026-02-18 | 639 | 6.015 | 495 | 6.577 | 1.515 |
| 2026-05-20 | 664 | 5.905 | 483 | 6.577 | 1.782 |
| 2026-08-19 | 759 | 5.725 | 557 | 6.394 | 1.796 |

- In 33 von 47 Perioden ergaebe die MSCI-Regel einen NIEDRIGEREN Boden, im Median haelt sie
  472 Titel zusaetzlich im Universum, max 1.851.
- Grund: unsere Regel sitzt immer exakt auf 99 %, MSCIs Rang wandert im Band und landet meist
  an der 99,25er-Kante. Die Uebernahme verschoebe unser All-Cap-Ziel faktisch von 99 auf 99,25 %.
- NIVEAU-VALIDIERUNG: MSCIs publizierter EUMSR liegt im Mai 2026 bei 537 Mio USD. Unsere heutige
  Regel kommt zum selben Termin auf 664 Mio (+24 %), die Rang-Mitnahme auf 483 Mio (-10 %).
  Der Vergleich ist eine Indikation, kein Beweis, weil die Universen nicht identisch sind.
- WIRKUNG AUFS PRODUKT: die zusaetzlichen Titel landen im Waterfall fast alle als Micro Cap. Der
  Standard-Index (Large+Mid) aendert sich nur indirekt ueber den verschobenen Coverage-Nenner.
  IMI und All Cap wachsen dagegen spuerbar.
- In den ersten Perioden liegen beide Regeln nahezu gleichauf, die Schere oeffnet sich mit der
  Zeit. Die Rang-Mitnahme braucht Zustand ueber Perioden, ist also wie der Size Buffer nur im
  Multi-Period-Lauf definiert.

## Groessen-Waiver eingebaut (2026-09-08, NICHT committet)

ENTSCHEIDUNG Nico: der Mindest-Free-Float-Waiver haengt an 2,0 x EUMSS-Boden (relativ,
skaliert mit dem Boden). Umgesetzt:

- `pipeline_core.py`: neuer Parameter `ff_waiver_k` (Default 0.0 = aus, verhaltensneutral).
  Der EUMSS-Filter ist in `size_ok` und `ff_ok` zerlegt; der Waiver hebt NUR das FF-%-Bein auf,
  wenn `Free Float MCap >= ff_waiver_k * eumss_full`. Rueckgabe um `ff_waiver_k` und
  `n_ff_waived` erweitert.
- `pipeline_core.py`: zusaetzlich `eumss_maint_ratio` (Default None = 1.0 = aus). Incumbents
  werden dann gegen `ratio x Boden` geprueft statt gegen den vollen Boden, auf BEIDEN
  Groessenbeinen. Gebaut fuer die Bestandsschutz-Messung, im Tool noch nicht verdrahtet.
- `naroix_benchmark.py`: Sidebar-Feld "FF-Waiver (x Boden)" unter Groessenboden (EUMSS),
  Default 2,0, mit Plausibilitaetspruefung. Kriterienbox zeigt Vielfaches und die daraus
  folgende absolute Float-Schwelle, Settings-Blatt protokolliert es.
- Tests: 312 -> 328 PASS, 0 FAIL. Vier Signatur-Checks, drei Verdrahtungs-Checks, sechs
  Waiver-Integrationschecks (Obermenge, Zaehler stimmt, jeder Zugang reisst wirklich die
  FF-%-Huerde und erreicht 2,0 x Boden, Groessenbeine gelten weiter, k=0 identisch),
  drei Maintenance-Checks.

BUG DABEI GEFUNDEN UND BEHOBEN: `eumss_coverage` wurde nur an 3 der 5
`run_selection_pipeline`-Aufrufstellen durchgereicht. Es fehlte ausgerechnet in den beiden
MULTI-PERIOD-Schleifen (Standard-MP und Europe-Pooled-MP), das Sidebar-Feld "Kalibrierpunkt"
war dort also wirkungslos. Der Eintrag vom 2026-09-07 ("an allen 5 Aufrufstellen durchgereicht")
war falsch. Neuer Test `test_ff_waiver_wired_in_app` sperrt beide Parameter gegen genau diesen
Fehler.

NICHT VERIFIZIERT: der Sidebar-Block selbst. AppTest kommt weiterhin nur bis zur Datenquelle
(`st.stop()` in der Sidebar), die neuen Felder sind damit nicht end-to-end geprueft.

## Nebenbefund: Segment auf Wertpapier- statt Firmenebene (2026-09-08)

Gemessen 19.08.2026 auf `gm_complete` (35.395 Zeilen, 35.140 Firmen):
- 242 Firmen mit mehreren Linien
- 76 davon mit Linien in VERSCHIEDENEN Segmenten
- 16 davon mit einem Teil im Standard-Index und einem Teil ausserhalb
- nur 1 Firma mit einem Split innerhalb des IMI (Grupo de Inversiones Suramericana, Mid/Small)

Beispiele: Carlsberg B Mid / A Micro, Teck B Mid / A Micro, Tele2 B Mid / A Micro, Svenska
Cellulosa B Mid / A Micro, Rogers B Mid / A Micro, Power Corp Large / Participating Micro,
Hyundai Motor drei Linien Large und eine Micro. Itau Unibanco Pfd Large / ON Micro und Banco
Santander Brasil Unit Large / Stammlinie Micro loesen sich mit dem neuen Waiver auf (beide
Stammlinien scheitern heute am 10-%-FF-Gate, nicht an der Groesse).
Alle sechs Anbieter vergeben das Segment firmenweit. MSCI woertlich: "all securities of a
company are always classified in the same size-segment."

## Bestandsschutz am Boden: Wirkung auf NX-EU-LM gemessen (2026-09-08, `cmp_floor_rules.py`)

Europe Pooled, 48 Perioden, Labeling zuerst, Cut-off 70/85, Halten 75/90. Endperiode gegen
MSCI Europe. Gegenprobe: H reproduziert A1 aus Messung 9 exakt (431 / 360 / 98,27 %).

| | H heute | R Rang-Mitnahme | M Maint 0,75 | RM beides | X Bestand frei | S kein Boden |
|---|---|---|---|---|---|---|
| Boden Endperiode Mio | 759 | 557 | 759 | 557 | 759 | 0 |
| Boden Median Mio | 349 | 301 | 349 | 301 | 349 | 0 |
| Titel Endperiode | 394 | 405 | 394 | 405 | 394 | 427 |
| Titel Median | 431 | 438 | 431 | 438 | 431 | 467 |
| Turnover in % | 3,47 | 3,40 | 3,47 | 3,40 | 3,47 | 3,35 |
| Standard-Coverage | 88,55 | 88,64 | 88,54 | 88,63 | 88,54 | 89,36 |
| MSCI Treffer | 360 | 367 | 360 | 367 | 360 | 377 |
| uns fehlend | 36 | 29 | 36 | 29 | 36 | 19 |
| nicht in MSCI | 34 | 38 | 34 | 38 | 34 | 50 |
| Abweichung gesamt | 70 | 67 | 70 | 67 | 70 | 69 |
| Gew. Overlap % | 98,27 | 98,59 | 98,27 | 98,59 | 98,27 | 99,02 |

BEFUNDE:
- DER BESTANDSSCHUTZ TUT FUER NX-EU-LM NICHTS. M (Maintenance 0,75) und X (Bestand komplett
  ausgenommen, MSCI/STOXX woertlich) sind auf JEDER Kennzahl identisch mit heute. Grund: der
  Boden bindet im EM-Small-Cap-Schwanz, nicht bei europaeischen Large und Mid Caps. Die Frage
  gehoert an All Cap / IMI und EM gemessen, nicht an diesem Produkt. Dort wurde sie separat
  gemessen: 409 liquide Titel in einer Periode, 23 bis 41 % der Pool-Abgaenge je nach k.
- WAS EUROPA BEWEGT, IST DAS NIVEAU DES BODENS, nicht der Bestandsschutz. Der Boden steuert den
  Pool, der den Coverage-Nenner bildet. Ein niedrigerer Boden zieht kleine europaeische Titel in
  den Nenner, alle bestehenden rutschen auf der Treppe nach unten, mehr passen unter die
  85er-Kante. R bringt 394 -> 405 Titel, 360 -> 367 Treffer, 98,27 -> 98,59 % Overlap bei
  gleichzeitig niedrigerem Turnover (3,47 -> 3,40 %).
- R HAT DIE KLEINSTE GESAMTABWEICHUNG (67 gegen 70 heute, 69 bei Solactive).
- SOLACTIVE (gar kein Boden) hat den besten gewichteten Overlap (99,02 %) und den niedrigsten
  Turnover (3,35 %), erkauft das aber mit 50 Nicht-MSCI-Titeln (heute 34) und einer
  Standard-Coverage von 89,36 %, die an die Obergrenze des MSCI-Zielbands 85 +/- 5 stoesst.
  36 Titel mehr als heute im Index.
- RM = R. Die Kombination bringt gegenueber R allein nichts, weil M ohnehin wirkungslos ist.

EMPFEHLUNG: Rang-Mitnahme (R) einbauen, Bestandsschutz zurueckstellen und an All Cap / EM
entscheiden. R ist von MSCI 3.1.2.2 und STOXX 3.3.1.2 woertlich abschreibbar, verbessert alle
vier Kennzahlen gleichzeitig und bringt den Boden von 759 auf 557 Mio, naeher an MSCIs
publizierte 537 Mio (Mai 2026).

Artefakt mit der vollstaendigen Kette und den offenen Punkten:
https://claude.ai/code/artifact/28fa9661-be94-4163-894a-d0f5cf96b918

## Bodenregel: Messung an All Cap und EM (2026-09-08, `cmp_floor_allcap.py`)

Die Europa-Messung war nicht aussagekraeftig fuer den Bestandsschutz. Nachgeholt an den
Produkten, wo der Boden bindet. 48 Perioden, Europe Pooled, Labeling zuerst, Cut-off 70/85.
Kein MSCI-Benchmark fuer diese Produkte, also Titelzahl und Turnover.

| | H heute | R Rang-Mitnahme | M Maint 0,75 | RM beides | S kein Boden |
|---|---|---|---|---|---|
| Boden Endperiode Mio | 759 | 557 | 759 | 557 | 0 |
| NX-GM-AC Titel Median | 8.764 | 9.652 | 9.093 | 9.892 | 12.607 |
| NX-GM-AC Turnover % | 9,48 | 8,37 | 8,28 | **7,55** | 9,18 |
| NX-EM-AC Titel Median | 4.054 | 4.623 | 4.390 | 4.783 | 6.766 |
| NX-EM-AC Turnover % | 13,11 | 11,04 | 10,47 | **9,46** | 10,94 |
| NX-EM-S Titel Median | 2.547 | 2.962 | 2.751 | 3.182 | 4.560 |
| NX-EM-S Turnover % | 21,42 | 17,65 | 17,17 | **14,57** | 15,92 |
| NX-GM-S Titel Median | 5.572 | 6.237 | 5.803 | 6.375 | 8.333 |
| NX-GM-S Turnover % | 15,74 | 13,66 | 13,75 | **12,39** | 14,03 |

BEFUNDE:
- DER BESTANDSSCHUTZ WIRKT SEHR WOHL, nur nicht in Europa. An NX-EM-S faellt der relative
  Turnover von 21,42 auf 17,17 % allein durch die Maintenance-Schwelle. Meine
  Zwischeneinschaetzung "zurueckstellen" ist damit erledigt.
- RM IST AUF ALLEN VIER PRODUKTEN DER BESTE RELATIVE TURNOVER, obwohl es unter den
  Boden-Varianten die meisten Titel haelt. Genau das soll eine Hysterese leisten.
- KEIN BODEN (S) IST DOMINIERT: mehr Titel als jede andere Variante (GM-AC Median +3.843,
  EM-AC +2.712) UND schlechterer relativer Turnover als RM auf allen vier Produkten. Als
  Methodik damit vom Tisch, als Research-Option bleibt sie im Tool.
- Turnover max bleibt bei allen Boden-Varianten praktisch gleich (rund 2.200 bei NX-GM-AC).
  Die Spitze kommt aus dem Datenbruch, nicht aus der Regel.
- Perioden mit Unterschied zu heute (NX-GM-AC): R 37 von 48, M 47 von 48, RM 47 von 48,
  S 48 von 48.

EMPFEHLUNG: Rang-Mitnahme UND Bestandsschutz 0,75, also RM. In Europa traegt R, an All Cap
und EM tragen beide.

## Bodenregel im Tool (2026-09-08, NICHT committet)

- `pipeline_core.py`: `eumss_carry_rank` und `eumss_carry_band` (Default None / 0.0, also aus).
  Die DM-Primary-Kurve wird jetzt mit `reset_index(drop=True)` positionsindiziert, damit ein
  Rang ueber Perioden weitergereicht werden kann. Rueckgabe um `eumss_rank_used` und
  `eumss_carry_band_used` erweitert.
- `naroix_benchmark.py`: Radio "Bodenregel" mit drei Optionen (Fest am Kalibrierpunkt /
  Mit Rang-Mitnahme / Kein Boden), Default FEST = heutiges Verhalten. Kalibrierpunkt,
  FF-Ratio und Bestandsschutz werden bei "Kein Boden" ausgegraut und neutralisiert.
  Neues Feld "Bestandsschutz (x Boden)", Default 0,75, mit Bereichspruefung 0 bis 1.
- Rang-Zustand: `_eumss_rank` in der Multi-Period-Hauptschleife, `_eumss_rank_ep` im
  Europe-Pooled-Lauf, beide aus `result["eumss_rank_used"]` der Vorperiode. Im
  Einzelperioden-Tab gibt es keinen Vorperioden-Rang, dort faellt die Regel bewusst auf den
  kalten Schnitt zurueck (steht im Hilfetext). ENTSCHEIDUNG Nico 2026-09-08: der
  Einzelperioden-Tab wird dabei nicht nachgezogen, RM gilt fuer den Multi-Period-Betrieb.
  Folge: derselbe Termin zeigt einzeln Boden 759 Mio und im MP-Lauf 557 Mio. Kein Fehler,
  aber beim Nebeneinanderlegen der Tabs zu wissen.
- NX-GM-TM bleibt an beiden Stellen hart `eumss_enabled=False`. Ein Test sperrt das:
  genau 3 Produktlaeufe an der Bodenregel, genau 2 Total-Markets-Laeufe ohne Boden.
- Kriterienbox zeigt Bodenregel, Bandobergrenze und Bestandsschutz; Settings-Blatt
  protokolliert alle vier Felder einzeln.

ENTSCHEIDUNG Nico 2026-09-08: Default ist RM, also Radio auf "Mit Rang-Mitnahme" und
Bestandsschutz 0,75. Das ist KEINE verhaltensneutrale Voreinstellung: jeder Lauf ohne
manuelle Umstellung weicht ab jetzt von allen Messungen ab, die vor dem 08.09.2026 entstanden
sind. Wer den alten Stand nachrechnen will, stellt Radio auf "Fest am Kalibrierpunkt" und
Bestandsschutz auf 1. Der Settings-Stempel protokolliert beide Felder, alte Exporte bleiben
also zuordenbar.

## Kumulationsbasis des Waterfalls (2026-09-08, `cmp_cum_basis.py`)

Frage: was passiert, wenn statt Adj_FF_MCap das rohe Free Float MCap kumuliert wird?
Antwort: die interessante Alternative ist eine dritte, nicht das rohe Float.

  A  Adj_FF_MCap                heute: Float x IF, IF enthaelt FOL UND China-Faktor 0,20
  B  Float x FOL (ohne China)   Inclusion Factor erst beim Gewicht
  C  Free Float MCap roh        ohne jede Auslandsbeschraenkung

48 Perioden, Rang-Mitnahme + Bestandsschutz 0,75, Label zuerst, Cut-off 70/85, Europe Pooled.
Gewichtung bleibt in ALLEN Varianten Adj_FF_MCap (`normalize_index_weight` haengt fest daran),
es geht ausschliesslich um die Segmentierung.

| | A heute | B Float x FOL | C Float roh |
|---|---|---|---|
| NX-EU-LM Titel Median | 438 | 438 | 438 |
| NX-EU-LM MSCI-Treffer / Overlap | 367 / 98,59 % | 367 / 98,59 % | 367 / 98,59 % |
| NX-EM-LM Titel Median | 1.497 | 2.420 | 2.414 |
| NX-EM-LM Turnover % | 8,92 | 8,60 | 8,60 |
| NX-GM-LM Titel Median | 3.366 | 4.339 | 4.332 |
| NX-GM-LM Turnover % | 5,86 | 6,27 | 6,26 |

BEFUNDE:
- EUROPA IST IN ALLEN DREI VARIANTEN IDENTISCH, bis auf die letzte Stelle. DM-Europa hat
  praktisch keine FOL und kein China. Saubere Kontrollprobe: der Effekt kommt nirgends sonst her.
- B UND C UNTERSCHEIDEN SICH UM 6 BIS 9 TITEL. Ausserhalb Chinas haben nur 1,3 % der Zeilen
  IF < 1. Die FOL-Kappung selbst ist auf diesen Daten also fast folgenlos. DIE GANZE FRAGE IST
  DER CHINA-FAKTOR.
- DER CHINA-FAKTOR IN DER KUMULATION KOSTET RUND 920 TITEL IM EM-STANDARD. Grund ist eine
  Asymmetrie: der Override maskiert auf EXCHANGE COUNTRY NAME == CHINA, der Waterfall gruppiert
  nach MAPPING COUNTRY. Im Markt CHINA bekommen A-Aktien (Boerse China) IF 0,20, H-Aktien und
  Red Chips (Boerse Hongkong) IF 1,0. Ein einheitlicher Faktor je Markt wuerde sich in der
  Coverage-Kurve herauskuerzen, dieser nicht: die Hongkong-Linien fressen das Coverage-Budget
  und druecken die A-Aktien nach Small und Micro.
- Nenner global: Float x FOL ist 1,035x Adj_FF, rohes Float 1,038x. Klein, weil China nur ein
  Teil des Universums ist; innerhalb Chinas ist der Faktor 5x.

WER MACHT WAS (aus den Regelwerken, woertlich geprueft):
- MSCI = B. "all share classes from the integrated China Equity Universe will be included ... as
  well as in the process of allocation of companies into the Size-Segments", IIF danach.
- STOXX = B. "The China Connect Scaling Factor is applied after the component screens and
  selection, and it is applied to the free float only at the final weighting of the components."
- MORNINGSTAR = B. "China A shares THAT HAVE BEEN ASSIGNED large-cap and mid-cap will be
  included ... at partial inclusion factor of 0.25 ... multiplied by factor of 0.25 for their
  WEIGHTING."
- BLOOMBERG = B im Ergebnis. Kein Phase-in-Faktor, sondern eine echte Kappung: "China A
  companies' free float percentage are capped at 28%", plus Industrie-FIL. Die Kappung steckt
  im Float und damit auch in der Segmentierung, wirkt aber wie ein FOL, nicht wie ein
  Aufnahmefaktor.
- SOLACTIVE = A, als einziger. "China A shares are included in the INDEX with an inclusion
  factor of 20%. The inclusion factor is taken into account when calculating the FINAL WEIGHTING
  FACTOR", und die FREE FLOAT MARKET CAPITALIZATION wird "adjusted by its FINAL WEIGHTING
  FACTOR", waehrend die Size Buckets auf der "accumulated FREE FLOAT MARKET CAPITALIZATION"
  beruhen. Das ist eine Lesart der Definitionen, keine ausdrueckliche Aussage zum
  Segmentierungsschritt wie bei STOXX und Morningstar.
- FTSE = eigene Variante, volle MCap. Die Frage stellt sich dort gar nicht.
- ROHES FLOAT (C) NUTZT NIEMAND.

FAZIT: die relevante Frage ist nicht A gegen C, sondern A gegen B, und dort stehen wir mit
Solactive allein gegen vier. Der Schalter fuer C existiert bereits (Sidebar "IF
Anwendungsmodus" -> "Gewichtung"), fuer B gibt es heute keinen. NICHT ENTSCHIEDEN, nur gemessen.

### Variante B im Detail (2026-09-08, `cmp_variant_b_detail.py`, Endperiode 19.08.2026)

Voller 48-Perioden-Pfad, ausgewertet wird die Endperiode.

| Produkt | A heute | B | Delta | Turnover A | Turnover B |
|---|---|---|---|---|---|
| NX-GM-LM | 3.613 | 4.521 | +908 | 197,3 | 271,9 |
| NX-EM-LM | 2.077 | 2.985 | +908 | 133,6 | 208,1 |
| NX-GM-AC | 10.134 | 10.352 | +218 | 746,5 | 750,7 |
| NX-EM-AC | 5.271 | 5.489 | +218 | 452,3 | 456,6 |
| NX-GM-S | 6.521 | 5.831 | -690 | 789,7 | 783,7 |
| NX-EM-S | 3.194 | 2.504 | -690 | 463,7 | 457,7 |
| NX-DM-LM | 1.536 | 1.536 | +0 | 64,2 | 64,2 |

- DM AENDERT SICH UM NULL. Alle 908 sind EM, praktisch alle China.
- ES IST EINE UMSCHICHTUNG, KEIN ZUWACHS: alle 908 Zugaenge zum Standard waren in A Small Cap.
  Gleichzeitig ruecken 218 Titel von Micro nach Small nach. 908 = 690 (Small-Verlust) + 218.
  Abgaenge aus dem Standard: NULL.
- Segmente im Markt CHINA (5.717 Titel, davon 4.407 A-Aktien und 1.310 ueber Hongkong):

  | | Large | Mid | Small | Micro |
  |---|---|---|---|---|
  | A: A-Aktien | 235 | 750 | 2.101 | 1.321 |
  | A: Hongkong | 157 | 131 | 151 | 871 |
  | B: A-Aktien | 760 | 1.052 | 1.488 | 1.107 |
  | B: Hongkong | 259 | 110 | 74 | 867 |

  Auch die Hongkong-Linien gewinnen im Large-Segment (+102), verlieren aber in Mid und Small.
  Der Markt-Nenner waechst, damit rutscht die 70er-Kante deutlich weiter nach unten im Ranking.
- NX-EM-LM Laendergewichte: CHINA 1.273 -> 2.181 Titel, Gewicht 21,19 -> 22,29 % (+1,10 pp).
  Alle anderen Laender unveraendert in der Titelzahl, minus 0,01 bis 0,32 pp Gewicht durch
  Verwaesserung. Taiwan -0,32, Korea -0,23, Indien -0,16.
- KOSTEN-NUTZEN: 908 zusaetzliche Positionen fuer 1,10 pp Gewichtsverschiebung. Der groesste
  Zugang traegt 0,018 % Indexgewicht, die meisten deutlich unter 0,01 %. Grund: die Gewichte
  laufen weiter auf Adj_FF, also mit dem 0,20-Faktor. Konzentration praktisch unveraendert
  (NX-GM-LM Top10 24,00 -> 23,95 %, Top100 51,93 -> 51,83 %, China 2,90 -> 3,08 %).
- TURNOVER im Standard steigt spuerbar: NX-GM-LM 197 -> 272 Wechsel im Mittel, relativ 5,5 auf
  6,0 %. All Cap und Small Cap bleiben praktisch unveraendert. Die Mid/Small-Kante liegt nach
  der Umstellung mitten im dichten A-Aktien-Feld.
- DATENFRAGE NEBENBEI: unter den groessten Zugaengen steht "Chagee Holdings Limited Unspons...",
  dem Namen nach eine unsponsored ADR-Linie. Vor einer Umstellung pruefen.

BEWERTUNG: methodisch spricht B klar dafuer (4 von 6 Anbietern, saubere Rangfolge innerhalb
Chinas). Operativ ist der Preis hoch: 908 Positionen mehr fuer 1,10 pp Exposure, hoeherer
Turnover, und der EM-Standard waechst von 2.077 auf 2.985 Titel, obwohl er mit MSCI EM (rund
1.200) ohnehin schon nicht vergleichbar ist. Der EM-Breite-Befund ist eine eigene Baustelle,
B macht ihn nur sichtbarer. NICHT ENTSCHIEDEN.

## ATVR-Kalibrierung auf Indien (2026-09-08, `cmp_atvr_sweep.py`)

Vorgabe Nico: Schwelle finden, bei der Indien im NX-GM-LM der Endperiode bei rund 1 % steht.
Setting: Labeling zuerst, Cut-off 70/85 mit Halten 75/90/99,5, Rang-Mitnahme, Kalibrierpunkt 99,
FF-Ratio 50, Bestandsschutz 0,75, Min FF 10, FF-Waiver 2,0, IF in der Selektion, Europe Pooled.
ADTV 1,0 / 0,75 Mio unveraendert. Variiert wurde nur das ATVR-Paar im MSCI-Verhaeltnis 20:15,
Maintenance = 2/3 der Entry-Schwelle.

| ATVR DM/EM | Titel GM-LM | Turnover % | INDIEN Titel | INDIEN Gewicht |
|---|---|---|---|---|
| 0 / 0 | 3.616 | 5,88 | 173 | 1,51 % |
| 2 / 1,5 | 3.616 | 5,89 | 173 | 1,51 % |
| 4 / 3 | 3.612 | 5,92 | 170 | 1,44 % |
| **6 / 4,5** | **3.598** | **5,94** | **156** | **1,00 %** |
| 8 / 6 | 3.573 | 5,94 | 131 | 0,64 % |
| 10 / 7,5 | 3.558 | 5,95 | 117 | 0,51 % |
| 14 / 10,5 | 3.512 | 5,92 | 74 | 0,25 % |
| 20 / 15 (MSCI) | 3.472 | 5,93 | 46 | 0,13 % |

SWEETSPOT: DM 6 % / EM 4,5 %, Maintenance 4 % / 3 %. Trifft die 1,00 % punktgenau.

BEFUNDE:
- AUSSERHALB INDIENS PASSIERT FAST NICHTS. Global verliert der Index 18 Titel (3.616 -> 3.598),
  davon 17 indische. China 2,89 -> 2,95, Taiwan 3,14 -> 3,20, Korea 2,28 -> 2,32: das sind reine
  Verwaesserungseffekte aus Indiens Gewichtsverlust, keine echten Zugaenge.
- TURNOVER BLEIBT UNVERAENDERT (5,88 -> 5,94 %). Der Screen kostet nichts an Stabilitaet.
- UNTER 3 % EM WIRKT DER SCHIRM GAR NICHT. Erst ab etwa 3 % beginnt er zu greifen, dann sehr
  steil: ein Prozentpunkt EM-Schwelle bewegt Indien um rund 0,3 bis 0,4 pp Gewicht.
- WARNUNG, WICHTIG: das ist die Kalibrierung eines Screens GEGEN EINEN DATENFEHLER. Indiens ADTV
  ist 10 bis 20-fach zu niedrig, weil der Master die IN-Titel als BSE statt NSE zieht. Eine
  EM-Schwelle von 4,5 % entspricht auf korrekten NSE-Daten grob 45 bis 90 % und wuerde Indien
  praktisch komplett entfernen. Fuer jedes andere EM-Land liegt 4,5 % dagegen weit unter MSCIs
  15 %, dort ist der Screen faktisch aus. Mit NSE-Daten springen alle 173 Titel wieder durch und
  Indien steht wieder bei 1,51 %.
- STOXX loest genau das per Regel: "For India volumes from National Stock Exchange ... are
  added" (Fussnote 5 zum Turnover-Ratio-Screen).
- OFFENE FRAGE ZUM ZIEL: 1,51 % liegt bereits unter dem, was Indien in den gaengigen globalen
  Benchmarks traegt. Eine Kuerzung auf 1,0 % vergroessert diesen Abstand. Ein ACWI-Referenzfile
  liegt nicht im Repo, der Vergleich ist also nicht nachgerechnet.

## ATVR scharf gestellt und ATVR-Doku korrigiert (2026-09-08, NICHT committet)

ENTSCHEIDUNG Nico: ATVR Entry 5 / 5, Maintenance 2,5 / 2,5, bewusst OHNE DM-EM-Unterschied.

BEGRUENDUNG (Nicos Argument, gemessen bestaetigt): unser absoluter ADTV-Screen ist symmetrisch
(1,0 / 0,75 Mio fuer DM wie EM). Ein asymmetrischer relativer Screen daneben laedt die Frage
ein "warum ATVR getrennt, ADTV aber nicht". Die beiden Regelwerksfamilien sind je fuer sich
konsistent: MSCI und STOXX trennen DM/EM beim ATVR (20/15), fuehren dafuer GAR KEINEN absoluten
Umsatzscreen. Solactive ist auf BEIDEN Beinen symmetrisch (ADTV 1,0/0,75 Mio, Liquidity Ratio
0,03 % / 0,015 % taeglich = annualisiert rund 7,6 / 3,8 %). Wir haben Solactives absolutes Bein
woertlich uebernommen, also gehoert das relative in dieselbe Struktur. Unser Niveau liegt
bewusst unter Solactive, solange die indischen Volumina von der BSE statt der NSE kommen.

MESSUNG (48 Perioden, Endperiode 19.08.2026, `cmp_atvr_sym.py`):

| Entry DM/EM | Maint DM/EM | GM-LM | DM-LM | EM-LM | Turnover | Indien |
|---|---|---|---|---|---|---|
| 0 / 0 | 0 / 0 | 3.616 | 1.538 | 2.078 | 5,88 % | 1,52 % |
| 5 / 5 | 2,5 / 2,5 | 3.590 | 1.538 | 2.052 | 5,90 % | 0,95 % |
| 10 / 5 | 5 / 2,5 | 3.590 | 1.538 | 2.052 | 5,90 % | 0,95 % |
| 7,6 / 7,6 (Solactive) | 3,8 / 3,8 | 3.560 | 1.538 | 2.022 | 5,90 % | 0,52 % |

- 5/5 UND 10/5 SIND BITGLEICH, bis auf die letzte Stelle. Der DM-Teil des Screens ist zwischen
  5 und 10 vollstaendig wirkungslos: es gibt keinen DM-Standard-Titel mit ATVR unter 10 %.
  Erst bei MSCIs 20 % fallen 8 DM-Titel. Die Symmetrie kostet also nichts.
- Kosten global: 26 Titel (3.616 -> 3.590), davon 25 indische. Turnover unveraendert.
- Bei Solactive-Niveau 7,6/3,8 verliert Indien die Haelfte (0,52 %). Dort waere zu pruefen, ob
  auch andere EM-Maerkte ausduennen; bei 5 % ist nachweislich nur Indien betroffen.

UMGESETZT
- Sidebar-Defaults: DM ATVR 5, EM ATVR 5, ATVR DM Maint. 2,5, ATVR EM Maint. 2,5. Alle vier
  Parser akzeptieren jetzt Komma und fallen auf den jeweiligen Default statt auf 0 zurueck.
- Zweite Caption unter den ATVR-Feldern haelt die Begruendung samt Quellen und dem
  NSE-Vorbehalt fest.
- "Labeling vor Liquiditaet" ist von `st.toggle(value=False)` auf `st.checkbox(value=True)`
  umgestellt, Hilfetext mit den Messwerten (431 statt 394 Titel, 360 statt 343 MSCI-Treffer,
  98,27 statt 97,54 % Overlap).

ZWEI ALTLASTEN DABEI BEHOBEN
- Die Sammelspalte `ATVR` rechnete `min(ATVR_3M, ATVR_12M)`, waehrend der Screen laengst 3M/6M
  prueft. Wer im Export nachsah, warum ein Titel durchfiel, las eine Zahl, die mit der Pruefung
  nichts zu tun hatte. Jetzt `min(ATVR_3M, ATVR_6M)`. `ATVR_12M` bleibt als eigene Spalte.
- Der Sidebar-Text behauptete "Screen MSCI-Stil auf 3M UND 12M". Korrigiert, samt Hinweis, dass
  3M/6M eine bewusste Abweichung ist.

Tests 349 -> 359+, alle Methodik-Defaults sind jetzt einzeln gesperrt (Labeling-Checkbox mit
value=True, Bodenregel Rang-Mitnahme, Bestandsschutz 0,75, FF-Waiver 2,0, ATVR 5/5 und 2,5/2,5)
plus vier Checks auf die ATVR-Spalte und die geprueften Horizonte.
