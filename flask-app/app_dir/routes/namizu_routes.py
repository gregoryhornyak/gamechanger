from flask import Blueprint, render_template, request, redirect, jsonify, url_for, session, flash, get_flashed_messages
from app_dir.utils.namizu_utils import save_comments, save_daily_poll, save_history, save_users_login, save_users_vote, save_visit_count, save_new_question
from app_dir.utils.namizu_utils import load_user_creds, load_user_login, load_user_votes, load_visit_count
from app_dir.utils.namizu_utils import load_today_poll, load_comments, load_question_bank, load_history
from app_dir.utils.namizu_utils import get_daily_question, get_new_question_id, get_vote_count, get_daily_results,get_comments_packet, get_user_names
from datetime import datetime
import random
import json
import re


bp = Blueprint('namizu', __name__, template_folder='templates')

@bp.route("/")
def index():
    return render_template('namizu_landing_page.html')

@bp.route("/poll", methods=['GET', 'POST'])
def main():
    daily_poll = get_daily_question()
    question = daily_poll["Question"]
    question_type = daily_poll["Type"]
    options = list(daily_poll["Answers"].keys())
    results = get_daily_results()
    vote_stat = load_user_votes()
    answers_ser_num = {}
    counter = 1
    for key, value in daily_poll["Answers"].items():
        answers_ser_num[counter] = {"key":key,"value":value}
        counter+=1

    # exclude
    vote_stats = {}
    for value in vote_stat.values():
        vote_stats[value["name"]] = value["voted"]

    vote_count = get_vote_count()
    submitted = False # if user submitted the form
    user = session["user"]
    comments_packet = get_comments_packet()
    
    if request.method == 'GET':    
        if vote_stats[user] == 1: # already voted
            submitted = True
    elif request.method == 'POST':
        if vote_stats[user] == 1: # already voted
            submitted = True
        if vote_count == 7: # all voted
            submitted = True
        if 'vote' in request.form and not submitted:
            if question_type == 3: # multichoice
                for opt in range(len(options)):
                    if str(opt+1) in request.form:
                        answers_ser_num[opt+1]["value"] += 1
                for details in answers_ser_num.values():
                    daily_poll["Answers"][details["key"]] = details["value"]

                save_daily_poll(daily_poll)
                vote_stats[user] = 1 # submitted vote
                save_users_vote(vote_stats)
                submitted = True
            else:    
                choice = request.form['vote']
                daily_poll["Answers"][choice] += 1

                save_daily_poll(daily_poll)
                vote_stats[user] = 1 # submitted vote
                save_users_vote(vote_stats)
                submitted = True

        if 'comment' in request.form:
            comment = request.form['comment']
            user = session["user"]
            current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            user_comments = load_comments()
            user_comments[current_date] = {
                user: comment
            }
            save_comments(user_comments)
            comments_packet = get_comments_packet()
    
    daily_poll = get_daily_question()
    question = daily_poll["Question"]
    question_type = daily_poll["Type"]
    options = list(daily_poll["Answers"].keys())
    results = daily_poll["Answers"]
    vote_stat = load_user_votes()
    vote_count = get_vote_count()
    return render_template('namizu_main.html', question=question, question_type=question_type,
                           options=options, results=results, form_submitted=submitted,
                           player_num=7, vote_count=vote_count, comments=comments_packet)

@bp.route("/calendar")
def calendar():
    return render_template('calendar.html')

@bp.get("/history/<target_date>")
def show_history(target_date):
    history = load_history()
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    target_date_uk_format = date_obj.strftime("%d-%m-%Y")
    if target_date_uk_format in history:
        history_log = history[target_date_uk_format]
        vote_count = sum(history_log["Answers"].values())
        player_count = len(history_log["Answers"])
        comments_packet = history_log["Comments"]
    else:
        return render_template('missing_history_log.html')
        
    return render_template('namizu_wayback_machine.html',question=history_log["Question"], 
                           results=history_log["Answers"], vote_count=vote_count, 
                           player_num=player_count, comments=comments_packet, date=target_date_uk_format)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    creds = load_user_creds()
    options = list(creds.keys())
    session["user"] = "noone"
    session.modified = True
    if request.method == "POST":
        visit_count = load_visit_count()
        visit_count["total"] += 1 # one more visitor
        save_visit_count(visit_count)
        user = request.form["vote"]
        password = request.form["password"]
        if creds[user] == password:
            session["user"] = user
            session.modified = True
            return redirect(url_for("namizu.main"),302)

    return render_template('namizu_login.html',options=options)

@bp.route("/snapshot")
def poll_snapshot():
    return f"<h1>DEPRECATED</h1>"
    question = get_daily_question()
    scores = load_scores()
    options = scores.keys()
    results = scores
    user_comments = load_comments()
    comments_packet = []
    vote_count = sum(scores.values())
    player_count = len(scores)
    current_date = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
    for timestamp, comments in user_comments.items():
        for usern, message in comments.items():
            comments_packet.append({"name": usern, "message": message})
    return render_template('poll_snapshot.html', question=question, options=options, 
                           vote_count=vote_count, results=results, player_num=player_count, comments=comments_packet, date=current_date)

@bp.route('/editor', methods=['GET', 'POST'])
def editor():
    # define variables
    question = "Do you think Geri would jump out of an airplane?"
    raw_question = "Do you think {P} would jump out of an airplane?" # goes into form
    options = ["Yes","No"]
    raw_options = ','.join(options) # goes into form
    qid = 0
    new_question_body = {}
    temp_q = {}
    submitted = False
    do_restart = False
    do_accept = False

    multichoice = False
    variable = False
    var_w_names = False
    var_w_options = False
    no_var_w_names = False
    yes_or_no = False
    # question types:
    # 0: No variables, names
    # 1: Variable(s), yes or no OR options
    # 2: Variable(s), names
    # 3: Multiselect (No variables), names
    q_type = 0 # default type

    if request.method == "GET":
        do_accept = False
        do_restart = False
        submitted = False
    if request.method == "POST":
        if "resp" in request.form:
            choice = request.form["resp"]
            if choice == "restart":
                do_restart = True
                flash("Session restarted by user")
            else:
                do_accept = True
        else:
            new_question = request.form["question"]
            new_answers = request.form["answers"]
            
            if "question_type" in request.form:
                multichoice = True if request.form["question_type"] == "multichoice" else False
            # categories:
            # if {P} in question -> regex
            # if nothing special in question -> read in raw
            # if {A} in question -> regex
            if "{" in new_question: # type 1 or 2
                variable = True
                text = new_question
                number_of_variables = text.count("{")
                # Names to replace
                names = get_user_names()
                selected_names = random.sample(names, number_of_variables)
                # Replace placeholders sequentially
                result = re.sub(r"{P}", lambda _: selected_names.pop(0), text)
                question = result
                
            else: # type 0 or 3
                question = new_question
            # if nothing in question -> names / options
            
            if new_answers != "names": # options
                options = new_answers.split(",")
                if len(options) > 6 or len(options) < 1: # too long or empty
                    # restart
                    do_restart = True
                    flash("Too many / too few options provided. Session restarted")
                for option in options:
                    if option == "":
                        do_restart = True
                        flash("Some options are empty. Session restarted")
                if variable:
                    var_w_options = True
                if "Yes" in options:
                    yes_or_no = True
            else: # render names
                options = get_user_names()
                if variable:
                    var_w_names = True

            """
            Q: Variable / No variable
            A: Names / Options / YesOrNo

            + Multichoice: Names / Options
            """

            if multichoice and yes_or_no:
                do_restart = True
                flash("Cannot be YesOrNo and Multichoice at the same time")

            if not multichoice and (no_var_w_names):
                q_type = 0
            if not multichoice and var_w_options:
                q_type = 1
            if not multichoice and var_w_names:
                q_type = 2
            if multichoice and not yes_or_no:
                q_type = 3            

            answers = {}
            for i in options:
                answers[i] = 0
            qid = get_new_question_id()
            qid = "Q"+str(qid)
            new_question_body = {
                
                "Type": q_type,
                "Question": question,
                "Answers": answers,
                "Status": 0
                
            }
            
            temp_q[qid] = new_question_body
            with open("database/temp_q.json","w") as f:
                json.dump(temp_q, f)
            submitted = True

    if do_restart:
        submitted = False
    if do_accept:
        try:
            with open("database/temp_q.json","r") as f:
                temp_q = json.load(f)
        except FileNotFoundError:
            temp_q = {}
        for k,v in temp_q.items():
            save_new_question(k,v)
            break
        flash("Submitted successfully")
    return render_template('namizu_new_question.html', question=question, raw_question=raw_question, 
                           options=options, raw_options=raw_options, form_submitted=submitted, multichoice=multichoice)


@bp.route("/admin")
def namizu_admin():
    visits = load_visit_count()
    visits = visits["total"]
    questions_bank = load_question_bank()
    logins = load_user_login()
    loginers = []
    for v in logins.values():
        if v["loggedin"] == 1:
            loginers.append(v["name"])
    if loginers:
        loginers = ', '.join(loginers)
    else:
        loginers = "No one"

    used_questions = 0
    for details in questions_bank.values():
        if details["Status"] == 2:
            used_questions += 1

    page_html = f"""
    <h1>ADMIN INFO</h1>
    <h2>naMizu has been visited {visits} times so far.<h2>
    <h2>{loginers} have logged in today so far.<h2>
    <h2>There are {len(questions_bank)} questions in the bank.</h2>
    <h2>{used_questions} questions have been used already.</h2>
    <h2>{int(used_questions/len(questions_bank)*100)}% of questions used.</h2>"""
    return page_html