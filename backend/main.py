from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional
import csv
from datetime import datetime, date
from pathlib import Path

app = FastAPI(title="Loto Calculator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Chemin vers le CSV (relatif au projet)
CSV_PATH = Path(__file__).parent.parent / "tirages.csv"
DAY_NAMES = {
    0: "LUNDI",
    2: "MERCREDI",
    5: "SAMEDI",
}
ALLOWED_DRAW_DAYS = set(DAY_NAMES.values())

# ── Barèmes des gains (montants moyens indicatifs en €)
GAINS_1T = {
    1: None,       # Jackpot — variable
    2: 111000,
    3: 1000,
    4: 100,
    5: 30,
    6: 10,
    7: 7,
    8: 4,
    9: 2.20,
}
GAINS_2T = {
    "R1": 100000,
    "R2": 500,
    "R3": 30,
    "R4": 3,
}

RANK_LABELS_1T = {
    1: "Rang 1 — JACKPOT 🏆",
    2: "Rang 2 — 5 numéros",
    3: "Rang 3 — 4 numéros + Chance",
    4: "Rang 4 — 4 numéros",
    5: "Rang 5 — 3 numéros + Chance",
    6: "Rang 6 — 3 numéros",
    7: "Rang 7 — 2 numéros + Chance",
    8: "Rang 8 — 2 numéros / 1 numéro + Chance",
    9: "Rang 9 — Chance seule (remboursement)",
}
RANK_LABELS_2T = {
    "R1": "Rang 1 2T — 5 numéros",
    "R2": "Rang 2 2T — 4 numéros",
    "R3": "Rang 3 2T — 3 numéros",
    "R4": "Rang 4 2T — 2 numéros",
}


# ── Modèles
class CalcRequest(BaseModel):
    numeros: list[int]          # 5 numéros principaux
    chance: int                  # numéro chance (1–10)
    date_debut: str              # format DD/MM/YYYY
    date_fin: str                # format DD/MM/YYYY
    second_tirage: bool = True   # option 2nd tirage activée
    nb_joueurs: int = 1          # pour diviser les gains
    jours_tirage: list[str] = ["SAMEDI"]

    @field_validator("numeros")
    @classmethod
    def check_numeros(cls, v):
        if len(v) != 5:
            raise ValueError("Exactement 5 numéros requis")
        if len(set(v)) != 5:
            raise ValueError("Les numéros doivent être distincts")
        for n in v:
            if not (1 <= n <= 49):
                raise ValueError(f"Numéro {n} hors plage (1–49)")
        return sorted(v)

    @field_validator("chance")
    @classmethod
    def check_chance(cls, v):
        if not (1 <= v <= 10):
            raise ValueError("Numéro Chance doit être entre 1 et 10")
        return v

    @field_validator("nb_joueurs")
    @classmethod
    def check_joueurs(cls, v):
        if v < 1:
            raise ValueError("Nombre de joueurs minimum : 1")
        return v

    @field_validator("jours_tirage")
    @classmethod
    def check_jours_tirage(cls, v):
        if not v:
            raise ValueError("Sélectionne au moins un jour de tirage")
        jours = []
        for jour in v:
            normalized = jour.strip().upper()
            if normalized not in ALLOWED_DRAW_DAYS:
                raise ValueError("Jours autorisés : LUNDI, MERCREDI, SAMEDI")
            if normalized not in jours:
                jours.append(normalized)
        return jours


# ── Lecture du CSV
def load_draws(csv_path: Path) -> list[dict]:
    draws = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                d = datetime.strptime(row["date"].strip(), "%d/%m/%Y").date()
                draws.append({
                    "date": d,
                    "date_str": row["date"].strip(),
                    "jour": DAY_NAMES.get(d.weekday()),
                    "n": [int(row[f"n{i}"]) for i in range(1, 6)],
                    "chance": int(row["chance"]),
                    "s2": [int(row[f"s{i}"]) for i in range(1, 6)]
                    if all(row.get(f"s{i}") for i in range(1, 6)) else None,
                })
            except Exception:
                continue
    return draws


# ── Calcul du rang 1er tirage
def get_rank_1t(hits: int, chance_hit: bool) -> Optional[int]:
    if hits == 5 and chance_hit:  return 1
    if hits == 5:                  return 2
    if hits == 4 and chance_hit:  return 3
    if hits == 4:                  return 4
    if hits == 3 and chance_hit:  return 5
    if hits == 3:                  return 6
    if hits == 2 and chance_hit:  return 7
    if hits == 2:                  return 8
    if chance_hit:                 return 9
    return None


# ── Calcul du rang 2nd tirage
def get_rank_2t(hits: int) -> Optional[str]:
    if hits == 5: return "R1"
    if hits == 4: return "R2"
    if hits == 3: return "R3"
    if hits == 2: return "R4"
    return None


# ── Route principale
@app.post("/calculer")
def calculer(req: CalcRequest):
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail=f"Fichier CSV introuvable : {CSV_PATH}")

    try:
        d_debut = datetime.strptime(req.date_debut, "%d/%m/%Y").date()
        d_fin   = datetime.strptime(req.date_fin,   "%d/%m/%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide (attendu DD/MM/YYYY)")

    if d_debut > d_fin:
        raise HTTPException(status_code=400, detail="La date de début doit être avant la date de fin")

    draws = load_draws(CSV_PATH)
    my_nums = set(req.numeros)
    my_c    = req.chance
    selected_days = set(req.jours_tirage)
    prix_grille = 3.0 if req.second_tirage else 2.20

    results = []
    total_gains = 0.0
    nb_tirages  = 0
    nb_gagnants = 0

    for draw in draws:
        if not (d_debut <= draw["date"] <= d_fin):
            continue

        # On ne garde que les jours sélectionnés (lundi, mercredi, samedi)
        if draw["jour"] not in selected_days:
            continue

        nb_tirages += 1
        has_gain = False

        # ── 1er tirage
        hits_1t   = len(my_nums & set(draw["n"]))
        chance_hit = draw["chance"] == my_c
        rank_1t   = get_rank_1t(hits_1t, chance_hit)
        gain_1t   = GAINS_1T.get(rank_1t) if rank_1t else None

        # ── 2nd tirage
        rank_2t  = None
        gain_2t  = None
        hits_2t  = 0
        if req.second_tirage and draw["s2"]:
            hits_2t  = len(my_nums & set(draw["s2"]))
            rank_2t  = get_rank_2t(hits_2t)
            gain_2t  = GAINS_2T.get(rank_2t) if rank_2t else None

        if rank_1t or rank_2t:
            has_gain = True
            nb_gagnants += 1

        g1 = gain_1t or 0
        g2 = gain_2t or 0
        total_draw = g1 + g2
        total_gains += total_draw

        results.append({
            "date": draw["date_str"],
            "jour": draw["jour"],
            "tirage_1": {
                "numeros": draw["n"],
                "chance": draw["chance"],
                "hits": hits_1t,
                "chance_hit": chance_hit,
                "rank": rank_1t,
                "rank_label": RANK_LABELS_1T.get(rank_1t) if rank_1t else None,
                "gain": gain_1t,
                "jackpot": rank_1t == 1,
            },
            "tirage_2": {
                "numeros": draw["s2"] if req.second_tirage else None,
                "hits": hits_2t if req.second_tirage else 0,
                "rank": rank_2t,
                "rank_label": RANK_LABELS_2T.get(rank_2t) if rank_2t else None,
                "gain": gain_2t,
            } if req.second_tirage else None,
            "gain_total_tirage": total_draw,
            "gain_par_joueur": round(total_draw / req.nb_joueurs, 2),
            "has_gain": has_gain,
        })

    mise_totale      = nb_tirages * prix_grille
    mise_par_joueur  = round(mise_totale / req.nb_joueurs, 2)
    gains_par_joueur = round(total_gains / req.nb_joueurs, 2)
    solde_par_joueur = round(gains_par_joueur - mise_par_joueur, 2)

    return {
        "resume": {
            "nb_tirages": nb_tirages,
            "nb_gagnants": nb_gagnants,
            "taux_gain_pct": round(nb_gagnants / nb_tirages * 100, 1) if nb_tirages else 0,
            "prix_grille": prix_grille,
            "mise_totale": round(mise_totale, 2),
            "mise_par_joueur": mise_par_joueur,
            "total_gains": round(total_gains, 2),
            "gains_par_joueur": gains_par_joueur,
            "solde_par_joueur": solde_par_joueur,
            "nb_joueurs": req.nb_joueurs,
            "second_tirage": req.second_tirage,
            "jours_tirage": req.jours_tirage,
        },
        "tirages": results,
    }


# ── Route santé
@app.get("/")
def health():
    return {"status": "ok", "csv": str(CSV_PATH), "csv_existe": CSV_PATH.exists()}


# ── Route pour lister les tirages disponibles dans le CSV
@app.get("/tirages-disponibles")
def tirages_disponibles():
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="CSV introuvable")
    draws = load_draws(CSV_PATH)
    dates = [d["date_str"] for d in sorted(draws, key=lambda x: x["date"])]
    return {
        "nb": len(dates),
        "premier": dates[0] if dates else None,
        "dernier": dates[-1] if dates else None,
        "dates": dates,
    }
