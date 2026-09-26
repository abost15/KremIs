# Byneset South – hull 9: teested rettet

## Endret
- **Teested:** de to gamle teeboksene er fjernet (den ene lå 30 m til høyre for
  hullet), og hullene i roughen er fylt igjen. Nytt L-formet teested er lagt inn
  (ca. 775 m²), med formen fra klubbens hulltegning og satellittbildet. Armen
  peker rett opp hullet, og foten går vestover.
- **Plassering:** teestedet står på linje med starten av fairway, slik det er
  bestemt ut fra kjennskap til banen. Det ligger 44,5 m vest for der
  satellittbildet viser det. Teestedet er skåret inn i roughen og høygresset,
  høyden følger terrenget, og kanten er skjøtt sømløst. Høygresset rundt
  utslaget er gjort om til rough i en ring på ca. 4 m, og tustene der er fjernet.
- **Teemarkører:** gul (bak) står på (−42,7, −9,8), rød på (−45,5, 5,2), 15 m
  foran. Begge er rettet mot midten av fairway.
- **Trær:** 14 lidar-trær er fjernet (088, 089, 091–102). De står på åpent
  gress både på satellittbildet og på tegningen. Innbakt skygge fra dem i
  vertex-fargene er fjernet.
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
Posisjonen styres av `SHIFT` i skriptet.

## Ikke endret
Green, bunkere, fairway og hullinja.
