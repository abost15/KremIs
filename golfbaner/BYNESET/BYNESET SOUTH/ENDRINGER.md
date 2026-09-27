# Byneset South: rettet mot virkelige kilder

Alle filene er laget på nytt fra originalfilene i Drive med `tools/fix_south.py`,
med parameterne i `tools/params/`. Kilder:
- **OpenStreetMap:** teesteder (tegnet 2024), greener, bunkere og pin.
- **Kartverket NHM DTM 1 m:** høydemodellen, hentet via WCS.
- **Satellittbildet** `Byneset_Sor_satellitt_ren.jpg`.

## Hva som ble kontrollert på alle 27 hull (nord og sør)
- **Greener mot DTM:** 23 av 27 greener følger høydemodellen med ca. 7 mm avvik,
  altså ekte break. Hull 6, 7, 8 og 9 på sørbanen var helt flate plan.
  Se `_kontroll/greener_mot_dtm.json`.
- **Teesteder, greener og bunkere mot OSM:**
  - Nordbanen stemmer overalt (IoU 0,98–1,0).
  - Sørbanen avvek på teestedene til hull 2, 5, 6, 7, 8 og 9.
  - Se `_kontroll/osm_sammenligning.json`.
- **Resten av terrenget mot DTM:** fairway, semi og rough stemmer. Teeputene
  er bevisst hevet ca. 15 cm og bunkerne senket ca. 15 cm.

## Endret (sørbanen)
| Hull | Teested fra OSM | Green på DTM | Trær fjernet |
|---|---|---|---|
| 2 | L-utslaget (1270691543) + teested 1270691579 | – | 1 |
| 3 | – | – | 1 |
| 4 | – | – | 4 |
| 5 | 1270691577 + 1270691576 | – | 4 |
| 6 | L-utslaget + 1270691579 (manglet i modellen) | ja | 4 |
| 7 | 1270339631 | ja | 3 |
| 8 | 1270339625 | ja | 3 |
| 9 | L-utslaget, armen heller mot fairway | ja | 14 |

- **Teesteder:** de gamle teeputene som overlappet OSM er fjernet. OSM-omrissene
  er skåret inn i terrenget med høyde fra DTM, og skjøtene er uten glipper.
  Teesteder som ikke finnes i OSM står urørt: hull 1, 3, 4 og det fremre
  teestedet på hull 2.
- **Markører:** står der de sto, hvis de fortsatt står på et teested. Ellers er
  de flyttet til nærmeste punkt inne på det nye utslaget. De er rettet langs
  spillelinja, og på hull 9 mot midten av fairway. Hullskilt og `CAM_Tee` er
  flyttet ut av utslaget der de ble dekket.
- **Greener (hull 6–9):** greenen og forgreenen ligger nå på DTM, med en jevn
  overgang på 3 m ut i omgivelsene. Hull, flagg og pin følger med, og `pin` og
  `elevation_change_tee_to_pin_m` i JSON er oppdatert.
- **Trær:** bare trær inne på banen (innenfor OSM-banegrensen), minst 8 m fra
  bygninger og 5 m fra veier, uten mørke piksler innenfor kronen + 2 m på
  satellittbildet. Alle står på gress, grussti eller høy. Se
  `_kontroll/fjernede_traer.png`. På hull 9 i tillegg de 14 trærne som
  klubbens hulltegning og satellittbildet viser som åpent gress. Innbakt skygge
  fra trærne er fjernet fra vertex-fargene.

## Rettet i JSON etter kontrollen mot klubbens scorekort
- **Hull 2:** hadde det delte teestedet til hull 6/9 oppført som sitt tredje tee
  (285 m mot en bakerste tee på 250 m). Fjernet fra `tees`; nå 2 tees på 245 og
  225 m mot klubbens 250 og 230.
- **Hull 5:** det fremre teestedet (OSM way 1270691576) manglet i `tees`, selv om
  klubben oppgir to lengder. Lagt til; nå 137 og 105 m mot klubbens 132 og 100.
- **Hull 9:** hadde teestedet til hull 2 oppført som bakerste tee. Fjernet
  tidligere. Markørene gir nå 263 og 251 m mot klubbens 265 og 250.
- **Indeksfila:** `tees`-tellingen for hull 2, 3 og 5 stemte ikke med JSON-ene.
- Det L-formede teestedet deles av hull 6 og 9: hull 6 spiller 239 m (klubb 240)
  og hull 9 spiller 263 m (klubb 265) fra hver sin del av det.

## Vurdert, men bevisst ikke endret
- **Fairway rundt par 3-greenene (hull 3, 7, 8):** modellen har semi-rough i
  ringen rundt greenen, mens den har fairway der på par 4 og 5 (41 % mot 6 % i
  ringen 3–12 m ut). Samme spørsmål ble vurdert på nordbanen, der OSM og et
  skarpt flyfoto viser at ringen er klippet. Eieren har valgt å la den stå som
  semi-rough. Sørbanen har uansett ingen fairway-data i OSM å bygge på.
- Hull 5 har allerede fairway i ringen, i motsetning til de andre par 3-hullene.

## Hull 1 (rettet etter tilbakemelding fra eieren)

Eieren fant to ting i modellen. Begge er kontrollert og rettet:

- **Fairwayen sluttet brått 11,9 m foran greenen.** På de 26 andre hullene går
  den helt inn (0,0–0,8 m). Innspillet er nå klippet inn til forgreenen: 309 m²
  ny fairway med en 167 m² semi-kant rundt, med samme innsnevring mot greenen som
  de andre hullene har. Avstanden fairway–green er nå 0,77 m.
- **Det fremre teestedet var 8 m²,** og de røde markørene sto utenfor puta.
  Median for teeputene på anlegget er 164 m². Ny pute: 115 m² (7 × 17 m) rundt
  markørene, et plan med 0,50 % fall, 0,148 m over DTM, med 2 m voll ut i
  roughen. Det er slik de andre putene er bygget — de er målt til helt plane
  flater (ujevnhet 0,000 m) med 0,2–0,5 % fall, 0,135–0,150 m over terrenget.
  Markørene og bjørka i vollen er satt ned på nytt. Fremre tee måler nå 250,6 m
  til pinnen mot klubbens 270 m; den bakre måler 284,0 m mot 300 m (klubben
  måler langs spillelinja).

Endringene er gjort ved å flytte eksisterende flater mellom `SURF_`-objektene —
altså klippe gresset annerledes — i stedet for å bygge ny geometri. Bakken har
0,87 m trekanter i området, så omrisset blir like fint som før. Ingen punkt er
flyttet sidelengs, og de eneste høydene som er endret er teeputa og vollen rundt
den, der høyden er regnet ut fra én funksjon av posisjonen slik at punkter som
deles mellom to flater får samme høyde. Kontroll: 0 skjøter med glipe (mot 0 i
originalen), putetoppen er helt plan (ujevnhet 0,0000 m), og hvert prøvepunkt
langs innspillet treffer én flate — ingen overlapp mot forgreenen.
Skript: `tools/h1_fast.py`. Tall: `_kontroll/hull01_innspill_og_teested.json`.

## Ikke endret
- Nordbanen stemmer med OSM og DTM. Trærne der er ikke kontrollert, fordi det
  ikke finnes et satellittbilde for nordbanen i Drive.
- Fairway og hullinjer: det finnes ingen fairway-data for sørbanen i OSM, og
  flyfotoet er for grovt til å kontrollere dem.
- Trær utenfor banen, på tak og veier: der kan satellittbildet ikke skille ekte
  fra falske trær sikkert nok.

## Filer per hull
- `.blend`
- `.glb` (Draco) og `_plain.glb`, eksportert med originalens innstillinger
- `.json`: `tees` (med `outline_blender` og `osm_way`), `pin`, `stats` og
  `update_note`
- `App (delte teksturer)/holes/*.gltf` og `.bin`
- `byneset_south_index.json` er oppdatert. `tee_elev_masl` gjelder origo, som i
  originalen.
