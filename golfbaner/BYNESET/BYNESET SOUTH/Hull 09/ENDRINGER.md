# Byneset South – hull 9: teested rettet

Laget på nytt fra originalfilen. Kilder:
- **OpenStreetMap:** teested (way 1270691543, 2024), green, bunkere og pin.
  OSM-bunkerne treffer modellens bunkere innenfor 1,1 m.
- **Satellittbildet** `Byneset_Sor_satellitt_ren.jpg`.
- **Klubbens hulltegning** fra bynesetgolf.no.

## Endret
- **Teested:** den feilplasserte teeboksen er fjernet. Teestedet er nå OSM-omrisset
  1:1 (ca. 645 m², med litt avrundede hjørner). Det er L-formet, og armen heller
  ca. 11° mot venstre for linja fra tee til pin, altså mot fairway. Høyden følger
  terrenget, og kanten er skjøtt sømløst mot roughen.
- **Teemarkører:** står på armens akse. Gul (bak) står på (4,1, −8,3) og rød
  15 m foran, som klubbens lengder 265/250 m. Begge er rettet mot midten av
  fairway.
- **Trær:** 14 lidar-trær er fjernet (088, 089, 091–102). De står på åpent
  gress både på satellittbildet og på tegningen, og tre av dem sto inne på
  teestedet. Innbakt skygge fra dem i vertex-fargene er fjernet.
- **Hullskilt og `CAM_Tee`:** flyttet til det nye teestedet.
- **JSON / index:** `tees`, `stats` og `tee_note` i `byneset_south_09.json` er
  oppdatert. For hull 9 i `byneset_south_index.json` er `glb_MB`, `tris`,
  `tee_elev_masl` og `elev_change_m` oppdatert.

## Ikke endret
- Teestedet ved (30,7, −25,3) står som før. Ifølge OSM (1270691579) tilhører det
  et annet hull. I den gamle JSON-fila var det feilaktig oppført som tee for
  hull 9.
- Green, bunkere, fairway og hullinja.

## Filer
Filene er eksportert med samme innstillinger som originalene (Blender 5.2):
- `.glb`: Draco
- `_plain.glb`: uten komprimering
- app-glTF: Draco, med teksturer fra `../textures/`

Skriptet `tools/fix_south_09_tee.py` gjenskaper `.blend`-filen fra originalen.
