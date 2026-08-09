from flask import Flask, abort, redirect, render_template, request, session, url_for

from football_data import build_starting_clubs, countries, is_known_club
from session_store import create, discard, get
from simulation import advance_week, create_career, final_card_svg, resolve_decision, retire


app = Flask(__name__)
app.config["SECRET_KEY"] = "local-development-only-change-this-before-deploying"


def active_career():
    career_id = session.get("career_id")
    return get(career_id) if career_id else None


@app.get("/")
def new_career():
    return render_template("new_career.html", countries=countries())


@app.post("/career/start")
def start_career():
    country = request.form["country"]
    club = request.form["club"]
    known_countries = {member for members in countries().values() for member in members}
    if country not in known_countries or not is_known_club(club) or not request.form.get("position"):
        abort(400)
    old_id = session.pop("career_id", None)
    if old_id:
        discard(old_id)
    career = create_career(
        name=request.form["name"], country=country, position=request.form["position"],
        dominant_foot=request.form["dominant_foot"], starting_club=club,
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
    return render_template("career.html", career=current)


@app.post("/career/advance-week")
def advance_career_week():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
    if not current["pending_event"]:
        advance_week(current)
    return redirect(url_for("career"))


@app.post("/career/decision")
def decide():
    current = active_career()
    if not current or not current["pending_event"]:
        abort(400)
    resolve_decision(current, request.form.get("choice", ""))
    return redirect(url_for("career"))


@app.post("/career/retire")
def retire_career():
    current = active_career()
    if not current:
        return redirect(url_for("new_career"))
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
    try:
        return {"clubs": build_starting_clubs(country)}
    except KeyError:
        abort(400)


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=True
    )
