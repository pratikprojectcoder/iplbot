"""
IPL Bot — FastAPI Backend
Run: uvicorn api.main:app --reload (from IPLbot root)
"""
import os
import re
import sys
import json
import random

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predict_and_explain import predict_and_explain
from models.predict_match_input import build_match_input

app = FastAPI(title="IPL Bot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAM_FEATURES_PATH      = os.path.join(BASE, "processed", "team_features.csv")
VENUE_FEATURES_PATH     = os.path.join(BASE, "processed", "venue_features.csv")
PLAYER_FEATURES_PATH    = os.path.join(BASE, "processed", "player_features.csv")
SQUADS_2026_PATH        = os.path.join(BASE, "processed", "ipl_2026_squads.csv")
TEST_PREDICTIONS_PATH   = os.path.join(BASE, "processed", "test_predictions_with_confidence.csv")
IPL_JSON_DIR            = os.path.join(BASE, "ipl_json")
WEB_DIST                = os.path.join(BASE, "web", "dist")
WEB_DIST_ASSETS         = os.path.join(WEB_DIST, "assets")

# ─── Squad helpers ────────────────────────────────────────────────────────────
def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(name).lower()).strip()

def _short_name_key(name: str) -> str:
    parts = [p for p in _normalize_name(name).split() if p]
    if not parts:
        return ""
    return f"{parts[0][0]}_{parts[-1]}"

def _load_squads() -> dict:
    try:
        df = pd.read_csv(SQUADS_2026_PATH)
        df["team"]   = df["team"].astype(str).str.strip()
        df["player"] = df["player"].astype(str).str.strip()
        squad_map = {}
        for team, rows in df.groupby("team"):
            exact, short = set(), set()
            for p in rows["player"]:
                n = _normalize_name(p)
                if n:
                    exact.add(n)
                    short.add(_short_name_key(p))
            squad_map[team] = {"exact": exact, "short": short}
        return squad_map
    except Exception:
        return {}

SQUADS_2026 = _load_squads()

def _apply_squad_filter(df: pd.DataFrame, team: str) -> pd.DataFrame:
    if team not in SQUADS_2026:
        return df
    tp = SQUADS_2026[team]
    tmp = df.copy()
    tmp["_norm"]  = tmp["player"].apply(_normalize_name)
    tmp["_short"] = tmp["player"].apply(_short_name_key)
    return tmp[tmp["_norm"].isin(tp["exact"]) | tmp["_short"].isin(tp["short"])].copy()

def _latest_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.sort_values("date").groupby("player").tail(1).copy()

def _team_pool(df: pd.DataFrame, team: str, min_req: int):
    base = df[df["team"] == team].copy()
    base_lat = _latest_rows(base)
    if team not in SQUADS_2026:
        return base_lat, "historical"
    filt = _apply_squad_filter(base, team)
    filt_lat = _latest_rows(filt)
    if filt_lat["player"].nunique() >= min_req:
        return filt_lat, "squad_2026"
    return base_lat, "fallback_historical"

# ─── Match helpers ─────────────────────────────────────────────────────────────
def _build_match_index() -> Optional[pd.DataFrame]:
    rows = []
    if not os.path.isdir(IPL_JSON_DIR):
        return None
    for fname in os.listdir(IPL_JSON_DIR):
        if not fname.endswith(".json"):
            continue
        mid = fname.replace(".json", "")
        if not mid.isdigit():
            continue
        fpath = os.path.join(IPL_JSON_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            continue
        info  = raw.get("info", {})
        teams = info.get("teams", [])
        dates = info.get("dates", [])
        if len(teams) < 2 or not dates:
            continue
        dt = pd.to_datetime(dates[0], errors="coerce")
        if pd.isna(dt):
            continue
        rows.append({
            "match_id": int(mid),
            "date":     dt,
            "season":   int(dt.year),
            "team_a":   str(teams[0]).strip(),
            "team_b":   str(teams[1]).strip(),
            "venue":    str(info.get("venue", "")).strip(),
            "city":     str(info.get("city", "")).strip(),
        })
    if not rows:
        return None
    df = pd.DataFrame(rows).dropna(subset=["match_id", "date", "team_a", "team_b"])
    return df.sort_values(["date", "match_id"], ascending=[False, False]).reset_index(drop=True)

def _load_raw_json(match_id: int) -> Optional[dict]:
    path = os.path.join(IPL_JSON_DIR, f"{match_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _format_wicket(wk: dict, bowler: str) -> str:
    kind = (wk.get("kind") or "").lower()
    fielders = [
        (f.get("name") if isinstance(f, dict) else str(f))
        for f in wk.get("fielders", []) if f
    ]
    fn = fielders[0] if fielders else "?"
    if kind == "bowled":          return f"b {bowler}"
    if kind == "caught":          return f"c {fn} b {bowler}"
    if kind in ("caught and bowled", "c and b"): return f"c & b {bowler}"
    if kind == "lbw":             return f"lbw b {bowler}"
    if kind == "run out":         return f"run out ({fn})" if fielders else "run out"
    if kind == "stumped":         return f"st {fn} b {bowler}"
    if kind == "hit wicket":      return f"hit wkt b {bowler}"
    if kind == "retired hurt":    return "retired hurt"
    return f"b {bowler}"

def _innings_scorecard(inn: dict) -> dict:
    team = inn.get("team", "Unknown")
    batting_order, batting, bowling = [], {}, {}
    total_runs = 0
    legal_balls = 0

    def eb(name):
        if name not in batting:
            batting[name] = {"runs": 0, "balls": 0, "4s": 0, "6s": 0, "dismissal": None}
            batting_order.append(name)
        return batting[name]

    def ew(name):
        if name not in bowling:
            bowling[name] = {"balls": 0, "runs": 0, "wickets": 0}
        return bowling[name]

    for ov in inn.get("overs", []):
        for ball in ov.get("deliveries", []):
            batter = ball.get("batter")
            bowler = ball.get("bowler")
            if not batter or not bowler:
                continue
            runs   = ball.get("runs", {})
            rb, rt = runs.get("batter", 0), runs.get("total", 0)
            extras = ball.get("extras", {})
            bs = eb(batter)
            bs["runs"] += rb
            if rb == 4: bs["4s"] += 1
            elif rb == 6: bs["6s"] += 1
            if "wides" not in extras:
                bs["balls"] += 1
            bw = ew(bowler)
            bw["runs"] += rt
            if "wides" not in extras:
                bw["balls"] += 1
                legal_balls += 1
            wkts = ball.get("wickets", [])
            if wkts:
                bw["wickets"] += len(wkts)
                for wk in wkts:
                    po = wk.get("player_out")
                    if po:
                        eb(po)
                        if batting[po]["dismissal"] is None:
                            batting[po]["dismissal"] = _format_wicket(wk, bowler)
            total_runs += rt

    dismissals = sum(1 for n in batting_order if batting[n]["dismissal"] is not None)
    bat_rows = []
    for n in batting_order:
        s = batting[n]
        sr = round(100 * s["runs"] / s["balls"], 2) if s["balls"] > 0 else 0.0
        bat_rows.append({
            "batter":    n,
            "runs":      s["runs"],
            "balls":     s["balls"],
            "fours":     s["4s"],
            "sixes":     s["6s"],
            "sr":        sr,
            "dismissal": s["dismissal"] if s["dismissal"] else "not out",
        })

    bowl_rows = []
    for n, s in bowling.items():
        ovs = s["balls"] // 6 + (s["balls"] % 6) / 10.0
        econ = round(s["runs"] / ovs, 2) if ovs > 0 else 0.0
        bowl_rows.append({
            "bowler":   n,
            "overs":    round(ovs, 1),
            "runs":     s["runs"],
            "wickets":  s["wickets"],
            "economy":  econ,
        })
    bowl_rows.sort(key=lambda x: -x["wickets"])

    return {
        "team":          team,
        "total_runs":    total_runs,
        "total_wickets": dismissals,
        "overs_bowled":  f"{legal_balls // 6}.{legal_balls % 6}",
        "batting":       bat_rows,
        "bowling":       bowl_rows,
    }

def _phase_seg(overs_data):
    phases = {p: {"runs": 0, "overs": 0} for p in ["powerplay", "middle", "death"]}
    for ov in overs_data:
        n = ov.get("over", 0)
        r = ov.get("runs", 0)
        ph = "powerplay" if 1 <= n <= 6 else ("middle" if n <= 15 else "death")
        phases[ph]["runs"]  += r
        phases[ph]["overs"] += 1
    for p in phases:
        o = phases[p]["overs"]
        phases[p]["run_rate"] = round(phases[p]["runs"] / o, 2) if o else 0
    return phases

def _momentum(overs_data):
    result, cum = [], 0
    for ov in overs_data:
        r, w = ov.get("runs", 0), ov.get("wickets", 0)
        score = (2 if r >= 12 else (-1 if r <= 4 else 0))
        score -= (2 if w >= 2 else (1 if w == 1 else 0))
        cum += score
        result.append({"over": ov.get("over", 0), "momentum": cum})
    return result

def _normalize_for_analysis(raw: dict):
    if "innings" in raw:
        inns = raw["innings"]
        if len(inns) < 2:
            raise ValueError("Need 2 innings")
        def extract(inn_obj):
            data = []
            for ov in inn_obj.get("overs", []):
                n  = ov.get("over", 0) + 1
                tr = sum(b.get("runs", {}).get("total", 0) for b in ov.get("deliveries", []))
                tw = sum(len(b.get("wickets", [])) if isinstance(b.get("wickets", []), list) else 0 for b in ov.get("deliveries", []))
                data.append({"over": n, "runs": tr, "wickets": tw})
            return data
        return {
            "team_a": inns[0].get("team", "Team A"),
            "team_b": inns[1].get("team", "Team B"),
            "team_a_overs_data": extract(inns[0]),
            "team_b_overs_data": extract(inns[1]),
        }
    raise ValueError("Unsupported format")

# ─── Pydantic models ──────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    team: str
    opponent: str
    venue: str

class PlayerPerfRequest(BaseModel):
    team: str
    opponent: str
    venue: Optional[str] = None

class BestXIRequest(BaseModel):
    team: str

class SquadStrengthRequest(BaseModel):
    team_a: str
    team_b: str

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/teams")
def get_teams():
    try:
        df = pd.read_csv(TEAM_FEATURES_PATH)
        teams = sorted(df["team"].dropna().unique().tolist())
        return {"teams": teams}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/venues")
def get_venues():
    try:
        df = pd.read_csv(VENUE_FEATURES_PATH)
        venues = sorted(df["venue"].dropna().unique().tolist())
        return {"venues": venues}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/match-index")
def get_match_index():
    df = _build_match_index()
    if df is None:
        return {"matches": []}
    df["date"] = df["date"].astype(str)
    return {"matches": df.to_dict(orient="records")}

@app.get("/api/scorecard/{match_id}")
def get_scorecard(match_id: int):
    raw = _load_raw_json(match_id)
    if raw is None:
        raise HTTPException(404, f"Match {match_id} not found")
    info    = raw.get("info", {})
    toss    = info.get("toss", {})
    outcome = info.get("outcome", {})
    scorecards = []
    for inn in raw.get("innings", []):
        if not inn.get("overs"):
            continue
        scorecards.append(_innings_scorecard(inn))
    return {
        "match_id": match_id,
        "toss":     toss,
        "outcome":  outcome,
        "innings":  scorecards,
    }

@app.post("/api/analyze-match/{match_id}")
def analyze_match(match_id: int):
    raw = _load_raw_json(match_id)
    if raw is None:
        raise HTTPException(404, f"Match {match_id} not found")
    try:
        md = _normalize_for_analysis(raw)
    except ValueError as e:
        raise HTTPException(400, str(e))

    a_overs = md["team_a_overs_data"]
    b_overs = md["team_b_overs_data"]
    a_runs  = sum(o["runs"] for o in a_overs)
    b_runs  = sum(o["runs"] for o in b_overs)
    a_rr    = a_runs / len(a_overs) if a_overs else 0
    b_rr    = b_runs / len(b_overs) if b_overs else 0
    rr_diff = a_rr - b_rr
    base    = 50
    adj     = rr_diff * 8 + (a_runs - b_runs) * 0.4
    a_prob  = max(0, min(100, base + adj))

    return {
        "team_a":           md["team_a"],
        "team_b":           md["team_b"],
        "winner":           md["team_a"] if a_runs > b_runs else md["team_b"],
        "margin":           abs(a_runs - b_runs),
        "team_a_phases":    _phase_seg(a_overs),
        "team_b_phases":    _phase_seg(b_overs),
        "team_a_momentum":  _momentum(a_overs),
        "team_b_momentum":  _momentum(b_overs),
        "win_probability":  {
            "team_a": round(a_prob, 1),
            "team_b": round(100 - a_prob, 1),
        },
    }

@app.post("/api/predict")
def predict(req: PredictRequest):
    try:
        result = predict_and_explain(req.team, req.opponent, req.venue)
        mi     = build_match_input(req.team, req.opponent, req.venue)
        row    = mi.iloc[0]
        extra_fields = [
            "team_batting_first_win_pct","opp_batting_first_win_pct","batting_first_win_pct_diff",
            "team_home_win_pct","opp_home_win_pct","home_win_pct_diff",
            "team_h2h_win_pct","opp_h2h_win_pct","h2h_win_pct_diff",
            "team_toss_win_pct","opp_toss_win_pct","toss_win_pct_diff",
        ]
        extras = {}
        for f in extra_fields:
            v = row.get(f)
            extras[f] = None if (v is None or (hasattr(v, '__float__') and __import__('math').isnan(float(v)))) else float(v)
        return {
            "prediction":  result["prediction"],
            "explanation": result["explanation"],
            "extras":      extras,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/model-accuracy")
def model_accuracy():
    try:
        df = pd.read_csv(TEST_PREDICTIONS_PATH)
        total = len(df)
        correct = int(df["correct_prediction"].sum())
        accuracy = round(correct / total * 100, 2) if total else 0
        avg_conf = round(df["prediction_confidence_pct"].mean(), 2) if total else 0

        def acc_at(threshold):
            sub = df[df["prediction_confidence_pct"] > threshold]
            if sub.empty: return 0.0, 0
            return round(sub["correct_prediction"].mean() * 100, 2), len(sub)

        a60, n60 = acc_at(60)
        a70, n70 = acc_at(70)
        a80, n80 = acc_at(80)

        sample = df[["date","team","opponent","venue","predicted_winner",
                      "actual_winner","prediction_confidence_pct","correct_prediction"]].head(20).to_dict(orient="records")
        return {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "avg_confidence": avg_conf,
            "by_confidence": {
                "60": {"accuracy": a60, "count": n60},
                "70": {"accuracy": a70, "count": n70},
                "80": {"accuracy": a80, "count": n80},
            },
            "sample": sample,
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/players/performance")
def player_performance(req: PlayerPerfRequest):
    try:
        df = pd.read_csv(PLAYER_FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        latest, mode = _team_pool(df, req.team, min_req=5)
        if latest.empty:
            raise HTTPException(404, f"No data for {req.team}")
        latest = latest.copy()
        latest["predicted_runs"] = (
            0.4 * latest["player_last5_runs_avg"] +
            0.3 * latest["player_vs_team_avg"] +
            0.3 * latest["player_at_venue_avg"]
        )
        latest["predicted_wickets"] = latest["player_last5_wickets"]
        cols_bat  = ["player","player_last5_runs_avg","player_last5_strike_rate","predicted_runs"]
        cols_bowl = ["player","player_last5_wickets","player_last5_economy","predicted_wickets"]
        top_bat  = latest.sort_values("predicted_runs", ascending=False).head(5)[cols_bat]
        top_bowl = latest.sort_values("predicted_wickets", ascending=False).head(5)[cols_bowl]
        return {
            "team":     req.team,
            "mode":     mode,
            "batters":  top_bat.round(2).to_dict(orient="records"),
            "bowlers":  top_bowl.round(2).to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/players/best-xi")
def best_xi(req: BestXIRequest):
    try:
        df = pd.read_csv(PLAYER_FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        latest, mode = _team_pool(df, req.team, min_req=11)
        if latest.empty:
            raise HTTPException(404, f"No data for {req.team}")
        latest = latest.copy()
        latest["score"] = (
            0.5 * latest["player_last5_runs_avg"] +
            0.3 * latest["player_last5_wickets"] -
            0.2 * latest["player_last5_economy"]
        )
        xi = latest.sort_values("score", ascending=False).head(11)
        cols = ["player","player_last5_runs_avg","player_last5_wickets","player_last5_economy","score"]
        return {
            "team": req.team,
            "mode": mode,
            "xi":   xi[cols].round(2).reset_index(drop=True).to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/players/leaders")
def season_leaders():
    try:
        df = pd.read_csv(PLAYER_FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        pooled = []
        teams  = sorted(SQUADS_2026.keys()) if SQUADS_2026 else sorted(df["team"].dropna().unique())
        for team in teams:
            lat, _ = _team_pool(df, team, min_req=5)
            if not lat.empty:
                pooled.append(lat)
        combined = pd.concat(pooled, ignore_index=True) if pooled else _latest_rows(df)
        oc = combined.sort_values("player_last5_runs_avg", ascending=False).head(10)[
            ["player","team","player_last5_runs_avg","player_last5_strike_rate"]
        ].round(2)
        pc = combined.sort_values("player_last5_wickets", ascending=False).head(10)[
            ["player","team","player_last5_wickets","player_last5_economy"]
        ].round(2)
        return {
            "orange_cap": oc.to_dict(orient="records"),
            "purple_cap": pc.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/players/squad-strength")
def squad_strength(req: SquadStrengthRequest):
    try:
        df = pd.read_csv(PLAYER_FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        results = {}
        for team in [req.team_a, req.team_b]:
            lat, mode = _team_pool(df, team, min_req=8)
            if lat.empty:
                raise HTTPException(404, f"No data for {team}")
            results[team] = {
                "mode":             mode,
                "batting_strength": round(float(lat["player_last5_runs_avg"].mean()), 2),
                "bowling_strength": round(float(lat["player_last5_wickets"].mean()), 2),
                "avg_strike_rate":  round(float(lat["player_last5_strike_rate"].mean()), 2),
                "avg_economy":      round(float(lat["player_last5_economy"].mean()), 2),
                "squad_size":       int(lat["player"].nunique()),
            }
        return {"team_a": req.team_a, "team_b": req.team_b, "data": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/stats")
def stats():
    """Dashboard stats."""
    try:
        team_df  = pd.read_csv(TEAM_FEATURES_PATH)
        venue_df = pd.read_csv(VENUE_FEATURES_PATH)
        matches  = _build_match_index()
        return {
            "total_teams":   int(team_df["team"].nunique()),
            "total_venues":  int(venue_df["venue"].nunique()),
            "total_matches": len(matches) if matches is not None else 0,
            "seasons":       int(matches["season"].nunique()) if matches is not None else 0,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── React production build (optional): run `npm run build` in ./web first ───
def _spa_index():
    return os.path.join(WEB_DIST, "index.html")


if os.path.isdir(WEB_DIST_ASSETS):
    app.mount(
        "/assets",
        StaticFiles(directory=WEB_DIST_ASSETS),
        name="web_assets",
    )


@app.get("/")
def spa_root():
    """Serve the Vite/React app when `web/dist` exists (single-port deployment)."""
    idx = _spa_index()
    if os.path.isfile(idx):
        return FileResponse(idx)
    return {
        "service": "IPL Bot API",
        "docs": "/docs",
        "frontend_dev": "cd web && npm run dev  (with uvicorn on :8000 for /api proxy)",
        "frontend_build": "cd web && npm run build  then reload this server to serve the UI at /",
    }


@app.get("/{full_path:path}")
def spa_client_routes(full_path: str):
    """History-mode React routes: return index.html unless path is API or static asset."""
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(404, "Not Found")
    idx = _spa_index()
    if os.path.isfile(idx):
        return FileResponse(idx)
    raise HTTPException(
        404,
        "React UI not built. From project root: cd web && npm run build",
    )
