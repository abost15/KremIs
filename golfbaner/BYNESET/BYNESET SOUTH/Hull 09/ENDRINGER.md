# Byneset South – hull 9: teested rettet

Grunnlag: klubbens hulltegning og satellittbildet `Byneset_Sor_satellitt_ren.jpg`,
registrert mot modellen via bunkerne (avvik ca. 1,5 m).

## Endret
- **Teested:** de to gamle teeboksene er fjernet (den ene lå 30 m til høyre for
  hullet), og hullene i roughen er fylt igjen. Nytt L-formet teested er lagt inn
  (ca. 775 m²): armen peker opp mot fairway, og foten går vestover langs
  trerekka, slik det er på tegningen og satellittbildet. Høyden følger terrenget,
  og kanten er skjøtt sømløst mot roughen.
- **Teemarkører:** gul (bak) står på (1,8, −9,5), rød på (−1,0, 5,5). De står
  15 m fra hverandre, som klubbens lengder 265/250 m, og er vendt mot spillelinja.
- **Trær:** 14 lidar-trær er fjernet (088, 089, 091–102). De står på åpent
  gress både på satellittbildet og på tegningen, og tre av dem sto midt i det
  nye teestedet. Innbakt skygge fra dem i roughens vertex-farger er fjernet.
- **Hullskilt og `CAM_Tee`:** flyttet til det nye teestedet.
- **JSON / index:** `tees`, `stats` og `tee_note` i `byneset_south_09.json` er
  oppdatert. For hull 9 i `byneset_south_index.json` er `glb_MB`, `tris`,
  `tee_elev_masl` og `elev_change_m` oppdatert.

## Filer
Filene er eksportert med samme innstillinger som originalene (Blender 5.2):
- `byneset_south_09.glb`: Draco
- `byneset_south_09_plain.glb`: uten komprimering
- `App (delte teksturer)/holes/byneset_south_09.gltf` og `.bin`: Draco, med
  teksturer fra `../textures/`

Skriptet `tools/fix_south_09_tee.py` gjenskaper `.blend`-filen fra originalen.

## Ikke endret
Green, bunkere, fairway og hullinja. De stemmer med tegningen innenfor noen få
meter.
