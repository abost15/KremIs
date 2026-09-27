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

## 5b. Klippe gresset om (fairway, semi, rough)

Fairwaykanten er bare en grense mellom to flater. Å flytte den er å klippe noen
trekanter som en annen gresstype. Trekantene i bakken er 0,3–1 m store, så du kan
male kanten omtrent hvor du vil.

1. Klikk på flaten du vil klippe **fra** — skal du utvide fairwayen, klikk på
   `SURF_Rough`.
2. Trykk **Tab**. Nå er du i Edit-modus.
3. Trykk **3** (velg flater), og **Alt + Z** så du ser gjennom flaten.
4. Velg trekantene du vil endre:
   - **C** gir deg en malepensel. Hold venstre musetast og mal. Rull på hjulet
     for å endre størrelsen. **Høyreklikk** avslutter penselen.
   - **B** gir en firkant du drar opp.
   - **Shift + klikk** legger til eller fjerner én trekant.
5. I Byneset-panelet, under **Klippe om gresset**, trykk **Fairway** (eller
   Semi, Rough, Tee).
6. Trykk **Tab** for å komme ut av Edit-modus og se resultatet.

Ble det for mye? Trykk **Ctrl + Z**, eller klipp flatene tilbake til Rough.

Fremgangsmåten er trygg: ingen punkter flyttes, så det kan ikke bli glipe mellom
flatene. Teksturskala, farger og lys blir regnet om automatisk.

Vil du ha en jevnere kant enn trekantene gir, si fra — da deler jeg opp
trekantene i det området først.

## 5c. Bygge et teested

1. **Venstreklikk** midt der puta skal ligge (3D-markøren flytter seg dit).
   Trykk **7** på talltastaturet først, så ser du rett ovenfra.
2. Trykk **Bygg teested her** i Byneset-panelet.
3. Du får en liten boks med mål. Standard er 7 × 17 m, som er vanlig størrelse
   her (median på anlegget er 164 m²).
   - **Bredde / Lengde**: målene på puta.
   - **Retning**: 0 betyr at puta peker mot pinnen. Skriv f.eks. 10 for å vri den
     10 grader.
   - **Høyde over terrenget**: 0,148 m er det de andre putene har.
   - **Voll ut i roughen**: hvor langt ut skråningen går. 2 m er standard.
4. Trykk **OK**.

Puta blir en helt plan flate med maks 0,5 % fall, som de andre putene på
anlegget, og terrenget rundt løftes i en voll opp til kanten. Markører, skilt og
trær som står i vollen blir satt ned på nytt.

Er den feil? **Ctrl + Z** og prøv igjen med andre tall. Du kan gjøre det så mange
ganger du vil.

Merk: puta legges der du klikker, oppå den bakken som er der. Skal teestedet
ligge et helt annet sted, flytt også de røde eller gule markørene dit (se 5).

## 6. Lagre og eksportere

1. **Ctrl + S** lagrer `.blend`-fila.
2. Trykk **Eksporter GLB** i Byneset-panelet.

Det lager `<hullnavn>.glb` og `<hullnavn>_plain.glb` i samme mappe, med nøyaktig
de samme innstillingene som originalfilene. Det er disse appen bruker.

## 7. Dette bør du ikke gjøre uten videre

- **Ikke flytt eller slett punkter i `SURF_`-flatene.** De henger sammen kant i
  kant, har innbakt lys i fargene og egne normaler. Flytter du et punkt i
  Edit-modus, blir det glipe mellom flatene og mørke flekker. Å *klippe om*
  flater (5b) og å bygge teested (5c) er trygt — de knappene rører ikke
  punktene sidelengs.
- **Vær forsiktig med green, forgreen og bunkere.** Klipper du bort flater helt
  inntil kanten der, kan det bli hull i bakken. Hold deg et par trekanter unna.
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

- finere kant enn trekantene gir (jeg deler dem opp først)
- endringer på greenens fall eller på bunkere
- flyttet eller nytt teested, siden lengdene i `.json` må regnes om
- flyttet pinne
- oppdatert `.json` og `byneset_south_index.json` etter endringer
- app-filene (`.gltf` + `.bin` med delte teksturer) eksportert på nytt
