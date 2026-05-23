# Loto Calculator

Calculateur de gains Loto FDJ avec:
- backend `FastAPI`
- frontend `HTML/CSS/JS` (vanilla)
- filtrage des tirages par jour (`LUNDI`, `MERCREDI`, `SAMEDI`)

## Structure

```text
loto-calculator/
├── loto_201911.csv      # Fichier source FDJ officiel (format ;)
├── tirages.csv          # Fichier normalise utilise par l'API
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   └── index.html
└── README.md
```

## Donnees CSV

L'API lit `tirages.csv` (a la racine).

Format attendu:

```csv
date,n1,n2,n3,n4,n5,chance,s1,s2,s3,s4,s5
```

Exemple:

```csv
20/05/2026,28,30,8,48,15,7,1,4,35,37,46
```

### Conversion depuis le fichier officiel FDJ

Le fichier `loto_201911.csv` est en format FDJ (`;`, colonnes longues). Si besoin, convertir vers `tirages.csv`:

```bash
cd /Users/saadelaboudi/Downloads/loto-calculator
/usr/local/bin/python3.14 - <<'PY'
import csv
from pathlib import Path

src = Path('loto_201911.csv')
dst = Path('tirages.csv')

with src.open('r', encoding='utf-8-sig', newline='') as f_in, dst.open('w', encoding='utf-8', newline='') as f_out:
    reader = csv.DictReader(f_in, delimiter=';')
    writer = csv.DictWriter(f_out, fieldnames=['date','n1','n2','n3','n4','n5','chance','s1','s2','s3','s4','s5'])
    writer.writeheader()
    for row in reader:
        writer.writerow({
            'date': row.get('date_de_tirage', '').strip(),
            'n1': row.get('boule_1', '').strip(),
            'n2': row.get('boule_2', '').strip(),
            'n3': row.get('boule_3', '').strip(),
            'n4': row.get('boule_4', '').strip(),
            'n5': row.get('boule_5', '').strip(),
            'chance': row.get('numero_chance', '').strip(),
            's1': row.get('boule_1_second_tirage', '').strip(),
            's2': row.get('boule_2_second_tirage', '').strip(),
            's3': row.get('boule_3_second_tirage', '').strip(),
            's4': row.get('boule_4_second_tirage', '').strip(),
            's5': row.get('boule_5_second_tirage', '').strip(),
        })

print('OK:', dst)
PY
```

## Installation et lancement

### 1. Creer un environnement Python local

```bash
cd /Users/saadelaboudi/Downloads/loto-calculator
/usr/local/bin/python3.14 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements.txt
```

### 2. Lancer le backend

```bash
cd /Users/saadelaboudi/Downloads/loto-calculator/backend
../.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API: `http://127.0.0.1:8000`
Swagger: `http://127.0.0.1:8000/docs`

### 3. Lancer le frontend

```bash
cd /Users/saadelaboudi/Downloads/loto-calculator/frontend
../.venv/bin/python -m http.server 3000 --bind 127.0.0.1
```

Interface: `http://127.0.0.1:3000`

## Utilisation

1. Choisir 5 numeros (1-49).
2. Choisir le numero Chance (1-10).
3. Definir la periode (`date_debut` / `date_fin`).
4. Choisir les jours de tirage a inclure (`LUNDI`, `MERCREDI`, `SAMEDI`).
5. Activer/desactiver l'option 2nd tirage.
6. Definir `nb_joueurs` si partage des gains.
7. Lancer le calcul.

Le tableau des resultats affiche maintenant aussi la colonne `Jour`.

## API

### `GET /`

Verifie l'etat du serveur et le CSV charge.

### `GET /tirages-disponibles`

Retourne les dates disponibles dans `tirages.csv`.

### `POST /calculer`

Exemple de payload:

```json
{
  "numeros": [9, 16, 29, 30, 41],
  "chance": 9,
  "date_debut": "01/01/2024",
  "date_fin": "31/12/2024",
  "second_tirage": true,
  "nb_joueurs": 3,
  "jours_tirage": ["LUNDI", "MERCREDI", "SAMEDI"]
}
```

## Bareme (estimations)

### 1er tirage
- Rang 1: 5N + Chance -> Jackpot
- Rang 2: 5N -> ~111000 EUR
- Rang 3: 4N + Chance -> ~1000 EUR
- Rang 4: 4N -> ~100 EUR
- Rang 5: 3N + Chance -> ~30 EUR
- Rang 6: 3N -> ~10 EUR
- Rang 7: 2N + Chance -> ~7 EUR
- Rang 8: 2N -> ~4 EUR
- Rang 9: Chance seule -> 2.20 EUR

### 2nd tirage
- R1: 5N -> ~100000 EUR
- R2: 4N -> ~500 EUR
- R3: 3N -> ~30 EUR
- R4: 2N -> ~3 EUR

Les gains sont indicatifs. Les rapports reels varient selon le nombre de gagnants.
