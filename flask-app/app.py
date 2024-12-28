from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import schedule
import time
from threading import Thread

app = Flask(__name__)

app.config['SECRET_KEY'] = 'k8e0boe2cf5e6ii3b1772ge3b95a157f'

# Initial variables to be displayed on subpages
page_values = {
    "apple": 0,
    "banana": 0,
    "coconut": 0,
    "dates": 0
}

def load_page_values():
    try:
        with open('player_score.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'apple': 0, 'banana': 0, 'coconut': 0, 'dates': 0}

def save_page_values(values):
    with open('player_score.json', 'w') as f:
        json.dump(values, f)


def load_scores():
    try:
        with open('player_rating.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'Bella': 0, 'Herczi': 0, 'Geri': 0, 'Bálint': 0, 'Márk': 0, 'Koppány': 0, 'Hanna': 0}

def save_scores(values):
    with open('player_rating.json', 'w') as f:
        json.dump(values, f)


@app.errorhandler(404)
def page_not_found(e):
    # You can render a custom template or return a message
    return render_template('404.html'), 404  # Returns a custom 404 page
       
@app.route('/')
@app.route('/home')
@app.route('/index')
@app.route('/zuhanoforint')
def home():
    return render_template('home.html')

@app.route('/gc')
def gchome():
    return render_template('gchome.html')

@app.route('/readme')
def readme():
    return render_template('readme')

@app.route('/gc/apple')
def apple():
    page_values = load_page_values()
    return render_template('apple.html', value=page_values["apple"])

@app.route('/gc/banana')
def banana():
    page_values = load_page_values()
    return render_template('banana.html', value=page_values["banana"])

@app.route('/gc/coconut')
def coconut():
    page_values = load_page_values()
    return render_template('coconut.html', value=page_values["coconut"])

@app.route('/gc/dates')
def dates():
    page_values = load_page_values()
    return render_template('dates.html', value=page_values["dates"])

@app.route('/gc/admin', methods=['GET', 'POST'])
def admin():
    page_values = load_page_values()
    if request.method == 'POST':
        for key in ['apple', 'banana', 'coconut', 'dates']:
            page_values[key] = int(request.form[f'{key}_new'])
        save_page_values(page_values)
        flash("Updated scores.")
        return redirect('/gc/admin')
    return render_template('admin.html', page_values=page_values)

@app.route("/gc/maze")
def maze():
    return render_template("minigame.html")

@app.route("/gc/wof")
def wof():
    return render_template("wheel_of_fortune.html")

@app.route("/gc/wofreal")
def wof_real():
    return render_template("wheel_of_fortune_real.html")

@app.route("/gc/quiz")
def game():
    return render_template("game01.html")

@app.route("/gc/loop1")
def loop1():
    return render_template("loop1.html")

@app.route("/gc/loop2")
def loop2():
    return render_template("loop2.html")

@app.route("/gc/loop3")
def loop3():
    return render_template("loop3.html")

@app.route("/gc/loop4")
def loop4():
    return render_template("loop4.html")

@app.route("/askus", methods=['GET', 'POST'])
def askus():
    question = "Who would be most likely to keep calm in absolutely stressful situations?"
    scores = load_scores()
    options = scores.keys()
    vote_count = 5
    #options = ["Anna", "Herczi", "Geri", "Bálint", "Márk", "Koppány", "Hanna"]
    if request.method == 'POST':
        choice = request.form['vote']
        scores[choice] += 1
        save_scores(scores)
        return redirect("/askus2")
    
    return render_template('askus.html', question=question,options=options, vote_count=vote_count)

@app.route('/scores')
def get_scores():
    # Return player scores as a JSON object
    return jsonify(load_scores())

@app.route('/askus2')
def askus_results():
    return render_template('askus2.html')

@app.route('/resetaskus')
def reset_scores():
    scores = load_scores()
    zero_scores = {key: 0 for key in scores}
    save_scores(zero_scores)
    return redirect("/askus2")

def zero_askus_score():
    scores = load_scores()
    zero_scores = {key: 0 for key in scores}
    save_scores(zero_scores)
    # change question

schedule.every().day.at("18:00").do(zero_askus_score)

# Function to run the scheduled tasks
def run_scheduled_tasks():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    # Start the scheduled task in the background
    thread = Thread(target=run_scheduled_tasks)
    thread.daemon = True
    thread.start()
    app.run(debug=False, use_reloader=False)
