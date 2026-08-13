import os
import random

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for

from database import get_club, get_club_by_name, get_clubs_by_country, get_country_by_name
from football_data import countries
from github_logo_urls import club_logo_url
from season_central import build_season_central
from session_store import create, discard, get
from simulation import advance_career, available_player_actions, create_career, ensure_career_state, final_card_svg, perform_player_action, resolve_decision, retire


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-only-change-this-before-deploying")


DATABASE_COUNTRY_NAMES = {
    "Argentina": "Argentina", "Belgium": "Bélgica", "Brazil": "Brasil", "England": "Inglaterra",
    "France": "França", "Germany": "Alemanha", "Italy": "Itália", "Netherlands": "Países Baixos",
    "Portugal": "Portugal", "Spain": "Espanha",
}


def database_country(country):
    name = DATABASE_COUNTRY_NAMES.get(country)
    return get_country_by_name(name) if name else None


def club_size(club):
    score = (club["reputation"] + club["strength"]) / 2
    return "small" if score < 56 else "medium" if score < 73 else "big"


def starting_clubs_from_database(country):
    record = database_country(country)
    if not record:
        return [], None
    available = get_clubs_by_country(record["code"])
    weighted = {"small": 85, "medium": 14, "big": 1}
    chosen = []
    while available and len(chosen) < 3:
        sizes = [club_size(item) for item in available]
        selected = random.choices(available, weights=[weighted[size] for size in sizes], k=1)[0]
        available.remove(selected)
        chosen.append({
            "id": selected["id"], "name": selected["name"], "size": club_size(selected),
            "league_country": record["name"], "logo": selected["logo"],
            "logo_url": club_logo_url(selected["logo"]),
        })
    return chosen, record


def current_club(career):
    """Resolve a referência do clube sem duplicar seus dados na carreira."""
    record = get_club(career.get("club_id")) if career.get("club_id") else None
    if record and record["name"] == career["club"]:
        record["logo_url"] = club_logo_url(record["logo"])
        return record
    country = database_country(career["player"]["country"])
    record = get_club_by_name(career["club"], country["code"]) if country else None
    career["club_id"] = record["id"] if record else None
    if record:
        record["logo_url"] = club_logo_url(record["logo"])
    return record


def hydrate_event_logo_urls(career):
    """Completa eventos em sessão criados antes da URL remota existir."""
    for event in [career.get("pending_event"), *career.get("event_queue", [])]:
        if not event:
            continue
        for candidate in event.get("transfer_candidates", []):
            candidate.setdefault("logo_url", club_logo_url(candidate.get("logo")))


def active_career():
    career_id = session.get("career_id")
    career = get(career_id) if career_id else None
    if not career:
        return None
    career = ensure_career_state(career)
    hydrate_event_logo_urls(career)
    return career


def career_stage_response(career):
    """Resposta única para fetch; o fallback continua sendo PRG para /career."""
    if request.accept_mimetypes.best == "application/json":
        return jsonify(ok=True, state="feedback" if career.get("pending_feedback") else "event" if career.get("pending_event") else "menu",
                       html=render_template("_gameplay_stage.html", career=career, player_actions=available_player_actions(career), season_central=build_season_central(career)),
                       hud={"overall": career["player"]["overall"], "form": career["player"]["form"],
                            "morale": career["player"]["morale"], "fitness": 100 - career["player"]["fatigue"],
                            "club": career["club"], "squad_status": career.get("squad_status_reason", "")})
    return redirect(url_for("career"))


@app.get("/")
def new_career():
    return render_template("new_career.html", countries=countries())


@app.post("/career/start")
def start_career():
    country = request.form.get("country", "")
    known_countries = {member for members in countries().values() for member in members}
    mode = request.form.get("mode", "realistic")
    country_record = database_country(country)
    try:
        club_id = int(request.form.get("club_id", ""))
    except ValueError:
        club_id = None
    club = get_club(club_id) if club_id else None
    if not club and request.form.get("club") and country_record:
        club = get_club_by_name(request.form["club"], country_record["code"])
    if country not in known_countries or not country_record or not club or club["country_code"] != country_record["code"] or not request.form.get("position") or mode not in {"realistic", "accelerated"}:
        abort(400)
    old_id = session.pop("career_id", None)
    if old_id:
        discard(old_id)
    career = create_career(
        name=request.form["name"], country=country, position=request.form["position"],
        dominant_foot=request.form["dominant_foot"], starting_club=club["name"], club_id=club["id"], mode=mode,
    )
    session["career_id"] = create(career)
    return redirect(url_for("career"))


@app.get("/career")
def career():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    if current["status"] in {"finished", "deceased"} and not current.get("pending_feedback"):
        return redirect(url_for("final_card"))
    return render_template("career.html", career=current, current_club=current_club(current), player_actions=available_player_actions(current), season_central=build_season_central(current))


@app.post("/career/season-central")
def season_central():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    current["career_view"] = request.form.get("view", "central")
    if current["career_view"] not in {"menu", "central", "standings", "calendar", "objectives", "history"}:
        abort(400)
    return career_stage_response(current)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/career/advance-week")
def advance_career_week():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    if current["status"] != "active":
        return redirect(url_for("final_card"))
    if not current["pending_event"]:
        advance_career(current)
    return career_stage_response(current)


@app.post("/career/decision")
def decide():
    current = active_career()
    if current and current["status"] != "active":
        return redirect(url_for("final_card"))
    if not current or not current["pending_event"]:
        abort(400)
    if not resolve_decision(current, request.form.get("choice", ""), request.form.get("event_id") or None):
        abort(400)
    return career_stage_response(current)


@app.post("/career/action")
def player_action():
    current = active_career()
    if not current or current["status"] != "active":
        return redirect(url_for("career"))
    if not perform_player_action(current, request.form.get("category", ""), request.form.get("action", "")):
        abort(400)
    return career_stage_response(current)


@app.post("/career/feedback/continue")
def consume_feedback():
    current = active_career()
    if not current or not current.get("pending_feedback"):
        abort(400)
    current["pending_feedback"] = None
    if (current.get("pending_event") or {}).get("type") == "outcome":
        current["pending_event"] = None
        from career_engine import _promote_next_event
        _promote_next_event(current)
    if current["status"] in {"finished", "deceased"}:
        return redirect(url_for("final_card"))
    return career_stage_response(current)


@app.post("/career/retire")
def retire_career():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    if current["status"] != "active":
        return redirect(url_for("final_card"))
    if current["player"]["age"] < 30:
        abort(400)
    from feedback_engine import feedback_snapshot, set_pending_feedback
    before = feedback_snapshot(current)
    retire(current, "Você decidiu encerrar a carreira profissional.")
    set_pending_feedback(current, "terminal", "Fim da carreira", current["retirement_reason"], before, terminal=True)
    return career_stage_response(current)


@app.get("/career/final-card")
def final_card():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    if current["status"] not in {"finished", "deceased"}:
        return redirect(url_for("career"))
    return render_template("career_card.html", career=current)


@app.get("/career/final-card.svg")
def download_final_card():
    current = active_career()
    if not current or current["status"] not in {"finished", "deceased"}:
        abort(404)
    return app.response_class(
        final_card_svg(current), mimetype="image/svg+xml",
        headers={"Content-Disposition": 'attachment; filename="vida-de-boleiro-card.svg"'},
    )


@app.post("/api/starting-clubs")
def starting_clubs():
    country = request.form.get("country", "")
    if country not in {member for members in countries().values() for member in members}:
        abort(400)
    clubs, country_record = starting_clubs_from_database(country)
    if not country_record:
        return {"clubs": [], "league_country": None, "message": "Ainda não há clubes cadastrados para este país."}
    return {"clubs": clubs, "league_country": country_record["name"]}


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
        use_reloader=True
    )
