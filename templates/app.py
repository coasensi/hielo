from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# Configuration de la base de données SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///progress.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modèle de la base de données pour enregistrer les performances
class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    difficulty = db.Column(db.String(20), nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    total_attempts = db.Column(db.Integer, nullable=False)

# Difficulté avec temps limite et paramètres
difficulties = {
    "easy": {"time_limit": 60, "operations": ["multiplication"], "range": [1, 10]},
    "medium": {"time_limit": 45, "operations": ["multiplication", "division"], "range": [1, 12]},
    "hard": {"time_limit": 30, "operations": ["multiplication", "division"], "range": [1, 20]},
}

# Stocker les sessions de jeu
game_sessions = {}  # {difficulty: {"start_time": datetime}}

# Suivi temporaire de la progression
user_progress = {"correct_answers": 0, "total_attempts": 0}

# Fonction pour générer une question
def generate_question(settings):
    operation = random.choice(settings["operations"])
    num1 = random.randint(*settings["range"])
    num2 = random.randint(*settings["range"])

    if operation == "multiplication":
        question = f"{num1} x {num2}"
        answer = num1 * num2
    elif operation == "division" and num2 != 0:
        question = f"{num1 * num2} / {num2}"
        answer = num1
    else:
        return generate_question(settings)  # Retry for division by zero
    return question, answer

# Route : Page d'accueil pour choisir la difficulté
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        difficulty = request.form["difficulty"]
        return redirect(url_for("game", difficulty=difficulty))
    return render_template("home.html", difficulties=difficulties.keys())

# Route : Jeu principal
@app.route("/game/<difficulty>", methods=["GET", "POST"])
def game(difficulty):
    settings = difficulties[difficulty]

    # Initialiser une session si elle n'existe pas
    if difficulty not in game_sessions:
        game_sessions[difficulty] = {"start_time": datetime.now()}

    # Vérifier la limite de temps
    elapsed_time = datetime.now() - game_sessions[difficulty]["start_time"]
    if elapsed_time.total_seconds() > settings["time_limit"]:
        save_progress_to_db(difficulty)
        del game_sessions[difficulty]
        return redirect(url_for("end"))

    # Gérer les réponses soumises
    if request.method == "POST":
        user_answer = int(request.form["user_answer"])
        correct_answer = int(request.form["correct_answer"])

        if user_answer == correct_answer:
            user_progress["correct_answers"] += 1
        user_progress["total_attempts"] += 1

    # Générer une nouvelle question
    question, answer = generate_question(settings)
    return render_template(
        "game.html",
        question=question,
        answer=answer,
        progress=user_progress,
        time_remaining=settings["time_limit"] - elapsed_time.total_seconds(),
    )

# Route : Fin du jeu
@app.route("/end")
def end():
    return render_template(
        "end.html",
        progress=user_progress,
        message="Temps écoulé ! Merci d'avoir joué.",
    )

# Route : Historique des performances
@app.route("/history")
def history():
    progress_records = Progress.query.order_by(Progress.timestamp.desc()).all()
    return render_template("history.html", records=progress_records)

# Enregistrer les progrès dans la base de données
def save_progress_to_db(difficulty):
    new_record = Progress(
        difficulty=difficulty,
        correct_answers=user_progress["correct_answers"],
        total_attempts=user_progress["total_attempts"],
    )
    db.session.add(new_record)
    db.session.commit()

# Initialiser la base de données
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
