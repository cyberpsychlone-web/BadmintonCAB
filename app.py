####################################################################################################################################
#   Version Date            Name        Description
####################################################################################################################################
#   0.0     09-Jul-2025     S.K.Sami    Basic court assignment, match records history store
#   0.1     12-Jul-2025     S.K.Sami    Timer pause, start fixed, Player reassignment right after match time completion
#   0.2     13-Jul-2025     S.K.Sami    Player rest fairness improvement, reset history in csv file
#   0.3     15-Jul-2025     S.K.Sami    Mac OS version
#   0.4     16-Jul-2025     S.K.Sami    Change of Court numbers input from number of courts
#   0.5     17-Jul-2025     S.K.Sami    Matching versions across all files only - no program update
#   0.6     17-Jul-2025     S.K.Sami    Bux fix on twice calling web browser, match history log
#   0.7     22-Jul-2025     S.K.Sami    New Shuttle-use counter addition
#   0.8		22-Jul-2025		S.K.Sami	UI addition - all settings popup in a modal from a settings button click
#   0.9     23-Jul-2025     S.K.Sami	Player names database and selection introduced, log file open with lock warning
#   1.0     24-Jul-2025     S.K.Sami	WSGI implementation, Name change to the app
#
#
#
#
#
####################################################################################################################################

import sys
from flask import Flask, render_template, request, jsonify, session, send_from_directory
import random, os, csv
from datetime import datetime
import webbrowser
import threading
import logging
import sys

# Set up logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


app = Flask(__name__)
app.secret_key = 'supersecretkey'

browser_opened = False  # Add this line

def open_browser():
    global browser_opened
    if not browser_opened:
        browser_opened = True
        webbrowser.open("http://127.0.0.1:5000")

def get_resource_path(filename, subfolder='static'):
    """Get full path to resource file whether in dev or PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # If running as a PyInstaller bundle
        base_path = os.path.join(sys._MEIPASS, subfolder)
    else:
        # Running in development mode
        base_path = os.path.join(os.path.abspath("."), subfolder)
    return os.path.join(base_path, filename)


import time

def log_match_history(round_num, court_assignments, resting_players, match_minutes, court_labels, shuttle_count):
    log_file = 'match_history_log.csv'
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    for i, court in enumerate(court_assignments):
        court_name = court_labels[i] if i < len(court_labels) else f'Court {i+1}'
        rows.append([
            round_num,
            timestamp,
            court_name,
            ', '.join(court),
            match_minutes,
            'Playing',
            shuttle_count
        ])
    rows.append([
        round_num,
        timestamp,
        'Resting',
        ', '.join(resting_players),
        match_minutes,
        'Resting',
        shuttle_count
    ])

    file_exists = os.path.isfile(log_file)
    max_retries = 5
    delay_seconds = 2

    for attempt in range(max_retries):
        try:
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Round', 'Timestamp', 'Location', 'Players', 'Duration (min)', 'Status', 'Shuttle Used'])
                writer.writerows(rows)
            break  # ✅ success, exit loop
        except PermissionError:
            logging.debug(f"[WARNING] Could not write to {log_file} (attempt {attempt + 1}/{max_retries}). File may be open in Excel.")
            time.sleep(delay_seconds)
    else:
        logging.debug(f"[ERROR] Failed to write to {log_file} after {max_retries} attempts. Skipping log for Round {round_num}.")


rest_history = {}
round_counter = 1
last_logged_round = 0

def assign_courts(players, num_courts):
    total_playing = num_courts * 4
    num_resting = max(0, len(players) - total_playing)

    if 'rest_index' not in session:
        session['rest_index'] = 0

    sorted_players = sorted(players)
    rest_index = session['rest_index']

    resting_players = [sorted_players[(rest_index + i) % len(sorted_players)] for i in range(num_resting)]
    playing_players = [p for p in sorted_players if p not in resting_players]
    random.shuffle(playing_players)

    court_assignments = [playing_players[i*4:(i+1)*4] for i in range(num_courts)]
    session['rest_index'] = (rest_index + num_resting) % len(sorted_players)

    return court_assignments, resting_players

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_players')
def get_players():
    player_file = get_resource_path('Players.csv')  # ← updated path
    players = []

    if os.path.exists(player_file):
        with open(player_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    players.append(row[0].strip())

    return jsonify({'players': players})



@app.route('/assign', methods=['POST'])
def reassign():
    global round_counter, last_logged_round

    data = request.json
    players = data.get('players', [])
    court_numbers = data.get('court_numbers', [])
    if isinstance(court_numbers, str):
        court_numbers = [x.strip() for x in court_numbers.split(',') if x.strip()]
    num_courts = len(court_numbers)
    match_minutes = int(data.get('match_minutes', 15))
    shuttle_count = int(data.get('shuttle_count', 0))

    court_assignments, resting_players = assign_courts(players, num_courts)

    if round_counter != last_logged_round:
        log_match_history(
            round_counter,
            court_assignments,
            resting_players,
            match_minutes,
            [f'Court {c}' for c in court_numbers],
            shuttle_count
        )
        last_logged_round = round_counter

    round_counter += 1

    logging.debug(f"[Info] Court allocation: {court_assignments}")
    logging.debug(f"[Info] Resting PLayers: {resting_players}")

    return jsonify({
        'court_assignments': court_assignments,
        'resting_players': resting_players,
        'court_labels': [f'Court {num}' for num in court_numbers]
    })

@app.route('/reset', methods=['POST'])
def reset_history():
    global rest_history, round_counter, last_logged_round
    session.clear()
    rest_history = {}
    round_counter = 1
    last_logged_round = 0

    log_file = 'match_history_log.csv'
    if os.path.isfile(log_file):
        with open(log_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Round', 'Timestamp', 'Location', 'Players', 'Duration (min)', 'Status'])

    logging.debug("[ALERT] History, session, and CSV log cleared.")
    return jsonify({'status': 'reset successful'})

# Browser launching now in WSGI
#if __name__ == '__main__':
#    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
#        threading.Timer(1.0, open_browser).start()
#    app.run(debug=True)
