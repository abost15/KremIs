# Byneset North: kontrollert mot virkelige kilder

Hele nordbanen (18 hull) er kontrollert mot OpenStreetMap, Kartverkets
høydemodell (NHM DTM 1 m) og flyfoto (Esri World Imagery, ca. 0,27 m/px, satt
sammen fra flisene og stedfestet mot OSM). Modellfilene, altså `.blend`, `.glb`
og app-glTF, er **ikke endret**. Bare tre JSON-filer er rettet.

## Hva som stemmer
- **Greener:** alle 18 treffer OSM med IoU 0,98–1,00, og alle følger
  høydemodellen med ca. 7 mm avvik. Break er altså ekte.
- **Fairway:** alle 18 treffer OSM-fairwayen med IoU 0,99–1,00. (Sørbanen har
  ingen fairway i OSM og kan derfor ikke etterprøves slik.)
- **Teesteder:** alle modellens teeputer treffer OSM med IoU 0,98–1,00.
- **Bunkere:** hver bunker ligger innenfor 1,1 m av OSM-bunkeren. Ingen mangler.
- **Pin:** ligger inne på greenen på alle 18. 12 av 27 greener på anlegget har
  en pin i OSM, og der treffer modellen eksakt.
- **Teemarkører:** står på en teepute på alle 18.
- **Trær:** 463 trær inne på banen ble testet mot flyfotoet. Ingen falske.
  Til sammenligning ble 27 falske funnet på sørbanen.
- **Terreng:** stikkprøve av fairway, semi, rough og tee mot høydemodellen
  viser avvik på 0,00 m i median.

## Rettet (bare metadata, modellen er urørt)
Tre hull hadde nabohullets teested oppført som sitt eget i `tees`. De ligger
20–40 m utenfor hullets spillelinje og er lengre enn klubbens bakerste tee:

| Hull | Fjernet teested | Tilhører | Lengder etter retting | Klubbens |
|---|---|---|---|---|
| 8 | OSM way 930377665 | hull 11 | 190, 147 m | 190, 160, 131, 131 |
| 11 | OSM way 930377664 | hull 8 | 338, 290, 265 m | 335, 285, 279, 260 |
| 15 | OSM way 930368331 | hull 5 | 447, 395 m | 465, 435, 435, 395 |

Hull 8 og 11 hadde byttet teested med hverandre. Teeputene ligger fortsatt i
3D-modellen der de skal; det var bare oppføringen i `tees` som var feil.

## Åpne spørsmål, ikke endret
- **Fairway rundt par 3-greenene (hull 2, 6, 8, 13):** OSM tegner en fairway-ring
  rundt greenen, mens modellen har en smal fairway-kant og semi-rough utenfor.
  Flyfotoet viser at området er klippet kortere enn rough, men ikke om det er
  fairway- eller semi-høyde. Geometrien er lik; bare klassen er ulik. Se
  `_kontroll/par3_fairway_spoersmaal.png`. Si fra om ringen skal være fairway.
- **Hull 4:** har fire teeputer, men den nest bakerste gir 388 m mens klubben
  oppgir 350 m. Den ligger rett på spillelinja, og ingen andre hull passer.
- **Hull 17 og 18:** nest bakerste tee er henholdsvis 19 og 18 m lengre enn
  klubbens tall. Kan komme av at klubben måler langs en annen spillelinje.
- **Færre teesteder enn klubben oppgir:** klubben lister fire lengder per hull,
  mens modellen har 1–4 teeputer. De som mangler, finnes heller ikke i OSM.
- **Trær utenfor banen:** ikke kontrollert. Mange står på tak og veier, men de
  påvirker ikke spill.

## Filer her
Bare JSON-filene, siden 3D-modellen ikke er endret. De tre rettede filene har
et `update_note`-felt. `.blend`, `.glb` og app-glTF ligger uendret i Drive.
