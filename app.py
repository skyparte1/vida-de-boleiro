import random

from flask import Flask, abort, redirect, render_template, request, session, url_for

from database import get_club, get_club_by_name, get_clubs_by_country, get_country_by_name
from football_data import countries
from github_logo_urls import club_logo_url
from session_store import create, discard, get
from simulation import advance_career, create_career, ensure_career_state, final_card_svg, resolve_decision, retire


app = Flask(__name__)
app.config["SECRET_KEY"] = "local-development-only-change-this-before-deploying"


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
    if current["status"] == "finished":
        return redirect(url_for("final_card"))
    return render_template("career.html", career=current, current_club=current_club(current))


@app.post("/career/advance-week")
def advance_career_week():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    if not current["pending_event"]:
        advance_career(current)
    return redirect(url_for("career"))


@app.post("/career/decision")
def decide():
    current = active_career()
    if not current or not current["pending_event"]:
        abort(400)
    if not resolve_decision(current, request.form.get("choice", ""), request.form.get("event_id") or None):
        abort(400)
    return redirect(url_for("career"))


@app.post("/career/retire")
def retire_career():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    if current["player"]["age"] < 30:
        abort(400)
    retire(current, "Você decidiu encerrar a carreira profissional.")
    return redirect(url_for("final_card"))


@app.get("/career/final-card")
def final_card():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    if current["status"] != "finished":
        return redirect(url_for("career"))
    return render_template("career_card.html", career=current)


@app.get("/career/final-card.svg")
def download_final_card():
    current = active_career()
    if not current or current["status"] != "finished":
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
        port=5000,
        debug=True,
        use_reloader=True
    )
