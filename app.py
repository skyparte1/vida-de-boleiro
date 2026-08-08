from flask import Flask, abort, redirect, render_template, request, session, url_for

from database import get_player, init_database, save_player
from football_data import build_starting_clubs, countries
from simulation import advance_season, create_player


app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-before-deploying"


@app.get("/")
def index():
    player_id = session.get("player_id")
    if player_id:
        return redirect(url_for("career", player_id=player_id))
    return redirect(url_for("new_career"))


@app.route("/new-career", methods=["GET", "POST"])
def new_career():
    if request.method == "POST":
        country = request.form["country"]
        club = request.form["club"]
        valid_clubs = set(session.get("starting_clubs", {}).get(country, []))
        if club not in valid_clubs:
            return render_template(
                "new_career.html",
                countries=countries(),
                error="Escolha um dos três clubes sugeridos para este país.",
            ), 400

        player = create_player(
            name=request.form["name"],
            age=int(request.form["age"]),
            country=country,
            position=request.form["position"],
            dominant_foot=request.form["dominant_foot"],
            club=club,
        )
        player_id = save_player(player)
        session["player_id"] = player_id
        return redirect(url_for("career", player_id=player_id))

    return render_template("new_career.html", countries=countries())


@app.post("/api/starting-clubs")
def starting_clubs():
    country = request.form.get("country", "")
    try:
        clubs = build_starting_clubs(country)
        session["starting_clubs"] = {country: [club["name"] for club in clubs]}
        return {"clubs": clubs}
    except KeyError:
        abort(400)


@app.get("/career/<int:player_id>")
def career(player_id):
    player = get_player(player_id)
    if not player:
        abort(404)
    return render_template("career.html", player=player)


@app.post("/career/<int:player_id>/advance")
def advance(player_id):
    player = get_player(player_id)
    if not player:
        abort(404)
    save_player(advance_season(player), player_id)
    return redirect(url_for("career", player_id=player_id))


if __name__ == "__main__":
    init_database()
    app.run(debug=True)
