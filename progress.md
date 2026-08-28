# progress

Rolling Snapshot des aktuellen Arbeitsstands. Kein Changelog, alte Punkte werden geloescht.

## Aktueller Fokus

Kundenrueckfrage zu "Europe Markets Index vs MSCI Europe" beantwortet (siehe Eintrag
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
