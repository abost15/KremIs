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

## Ikke endret
- Hull 1 hadde ingenting å rette.
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
