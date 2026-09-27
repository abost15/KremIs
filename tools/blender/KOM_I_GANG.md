# Redigere golfhullene i Blender

Skrevet for deg som ikke har brukt Blender før. Du trenger ikke kunne noe fra før.

## 1. Installer riktig versjon

Hullfilene er laget i **Blender 5.2**. Åpner du dem i en eldre versjon, kan ting
gå tapt. Last ned 5.2 (LTS) fra [blender.org/download/lts](https://www.blender.org/download/lts/).

## 2. Åpne et hull

Åpne `byneset_south_09.blend` (eller hvilket hull du vil) ved å dobbeltklikke.

**Slik beveger du deg:**

| Du vil | Gjør dette |
|---|---|
| Snurre rundt | Hold inne musehjulet og dra |
| Flytte deg sidelengs | Hold **Shift** + musehjulet og dra |
| Zoome | Rull på musehjulet |
| Se rett ovenfra | Trykk **7** på talltastaturet |
| Se hele hullet | Trykk **Home** |
| Zoome inn på det du har valgt | Trykk **.** på talltastaturet |

Har du ikke talltastatur, skru på *Edit → Preferences → Input → Emulate Numpad*.
Da bruker du vanlige talltaster i stedet.

## 3. Last inn verktøyet

I samme mappe ligger `byneset_verktoy.py`. Det gir deg noen knapper som gjør de
tingene som er lette å gjøre feil manuelt.

1. Klikk på fanen **Scripting** øverst i Blender.
2. Trykk **Open**, finn `byneset_verktoy.py` og åpne den.
3. Trykk på **play-knappen** (▶) over teksten.
4. Gå tilbake til fanen **Layout** og trykk **N**. Sidepanelet kommer fram til
   høyre, og der er fanen **Byneset**.

Dette må gjøres hver gang du starter Blender.

## 4. Hva ting heter

Alt i lista til høyre (Outliner) har navn som forteller hva det er:

| Navn | Hva det er |
|---|---|
| `SURF_Green`, `SURF_Fairway`, `SURF_Rough`, `SURF_Semi`, `SURF_Sand` | Selve bakken: green, fairway, rough, semi-rough, bunker |
| `SURF_Tee` | Teestedene |
| `TREE_Birch_042` | Et bjørketre. `Spruce` = gran, `Pine` = furu |
| `TEE_Marker_yellow_L` | Teemarkør, gul, venstre |
| `PIN_Cup`, `PIN_Flag`, `PIN_Stick` | Hullet, flagget og pinnen |
| `PROP_SignBoard`, `PROP_SignPost` | Hullskiltet |
| `CAM_Tee`, `CAM_Green` | Kameraene som brukes til bilder |

Målene er i meter. Punktet (0, 0) er bakerste teested, og **+Y peker mot
greenen**. Panelet viser hvor langt det valgte objektet er fra pinnen.

## 5. De vanligste endringene

### Flytte et tre
1. Klikk på treet.
2. Trykk **G** og dra musa. Klikk for å slippe, eller høyreklikk for å angre.
3. Vil du bare flytte sidelengs: trykk **G** og deretter **Z** to ganger
   (låser til bakkeplanet), eller **G** så **X** eller **Y** for én retning.
4. Trykk **Sett ned på bakken** i Byneset-panelet, så treet står riktig i terrenget.

### Snu et tre
Trykk **R**, så **Z**, og dra. Trær ser mer naturlige ut når de ikke er like.

### Gjøre et tre større eller mindre
Trykk **S** og dra. Trykk så **Sett ned på bakken**.

### Legge til et nytt tre
1. **Venstreklikk** der du vil ha det. Den røde/hvite ringen (3D-markøren)
   flytter seg dit. Får du den ikke flyttet, hold **Shift** og høyreklikk.
2. Klikk på et tre av den sorten du vil ha.
3. Trykk **Kopier tre hit** i Byneset-panelet.

Kopien får tilfeldig rotasjon og størrelse, og settes rett ned i bakken. Den
deler geometri med originalen, så fila vokser nesten ikke.

### Slette et tre
Klikk på det og trykk **X**, så **Delete**.

### Flytte teemarkørene
Velg begge to (klikk på den ene, **Shift**-klikk på den andre), trykk **G** og
flytt dem. Trykk så **Sett ned på bakken**. Husk at de bør stå på teeputa og
peke langs spilleretningen.

### Angre
**Ctrl + Z**. Det virker flere ganger bakover.

## 6. Lagre og eksportere

1. **Ctrl + S** lagrer `.blend`-fila.
2. Trykk **Eksporter GLB** i Byneset-panelet.

Det lager `<hullnavn>.glb` og `<hullnavn>_plain.glb` i samme mappe, med nøyaktig
de samme innstillingene som originalfilene. Det er disse appen bruker.

## 7. Dette bør du ikke gjøre uten videre

- **Ikke endre på `SURF_`-flatene** (green, fairway, rough og så videre). De
  henger sammen kant i kant, har innbakt lys i fargene og egne normaler. Går du
  inn i Edit-modus der, blir det fort skjøtefeil og mørke flekker. Si fra til
  meg i stedet, så gjør jeg det med skript.
- **Ikke flytt pinnen.** Posisjonen ligger også i `.json`-fila og brukes av
  appen. Verktøyet hopper over pinnen med vilje.
- **Ikke flytt eller skaler hele scenen.** Da mister modellen koblingen til
  virkelige koordinater.
- **Ikke lagre i en eldre Blender-versjon enn 5.2.**

## 8. Hvis noe blir feil

`.blend1`-fila ved siden av er forrige lagring. Døp den om til `.blend`, så er
du tilbake. Originalene ligger uansett i Drive og i GitHub.

## 9. Ting jeg må gjøre

Si fra hvis du vil ha:

- endringer på green, fairway, rough eller bunkere
- flyttet eller nytt teested, siden lengdene i `.json` må regnes om
- flyttet pinne
- oppdatert `.json` og `byneset_south_index.json` etter endringer
- app-filene (`.gltf` + `.bin` med delte teksturer) eksportert på nytt
