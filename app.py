from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin # UserMixin for our custom Firebase user
from datetime import datetime, date, timedelta, timezone # timedelta is needed for OTP expiration
from waitress import serve
import re
import os
from apscheduler.schedulers.background import BackgroundScheduler
import click
import random # For OTP generation
from datetime import datetime


# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore

# Import configurations and SMS handling functions
from config import Config
from sms_handler import send_sms, send_daily_mood_prompt_sms, format_phone_to_e164 # Removed send_otp_sms, handled in-app

# --- Application Initialization ---
app = Flask(__name__)
app.config.from_object(Config)
app.logger.setLevel("DEBUG")
# db.init_app(app) # REMOVE SQLAlchemy initialization

# --- Firebase Initialization ---
try:
    cred = credentials.Certificate(Config.GOOGLE_APPLICATION_CREDENTIALS)
    firebase_admin.initialize_app(cred)
    db_firestore = firestore.client() # Firestore client
    app_firebase_auth = firebase_auth # Firebase Auth client
    print("Firebase Admin SDK initialized successfully.")
    app.logger.info("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}. Ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly in .env and the file exists.")
    app.logger.error(f"Firebase initialization error: {e}")
    db_firestore = None
    app_firebase_auth = None
    # Optionally, exit the app if Firebase fails to initialize:
    # import sys
    # sys.exit("Could not initialize Firebase. Exiting.")


# --- Custom User Class for Flask-Login with Firebase ---
class FirebaseUser(UserMixin):
    def __init__(self, uid, phone_number=None, is_subscribed=False, consent_updated_at=None, **kwargs):
        self.id = uid # UserMixin expects an 'id' attribute
        self.uid = uid
        self.phone_number = phone_number
        self.is_subscribed = is_subscribed
        self.consent_updated_at = consent_updated_at
        # Store any other user data from Firestore
        for key, value in kwargs.items():
            setattr(self, key, value)

    @staticmethod
    def get(user_id): # user_id here is the Firebase UID
        if not db_firestore: return None
        try:
            user_doc = db_firestore.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                return FirebaseUser(uid=user_id, **user_data)
            return None
        except Exception as e:
            app.logger.error(f"Error fetching user {user_id} from Firestore: {e}")
            return None

@app.context_processor
def inject_global_vars():
    return {'current_year': '2025'}

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id): # user_id is Firebase UID from session
    return FirebaseUser.get(user_id)

# --- Temporary OTP Storage (In-memory, for simplicity. Use Redis/Firestore for production) ---
# This replaces OTP fields in the User model for this OTP flow.
# If using Firebase Phone Auth directly on client-side, this isn't needed.
# Since we are doing Twilio OTP -> then Firebase user creation/linking, we still manage OTP state briefly.
otp_store = {} # Format: { "phone_number_e164": {"otp": "123456", "expires_at": datetime_object} }

def generate_and_store_otp(phone_number_e164):
    otp_code = str(random.randint(100000, 999999))
    otp_store[phone_number_e164] = {
        "otp": otp_code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
    }
    return otp_code

def verify_stored_otp(phone_number_e164, otp_code):
    stored = otp_store.get(phone_number_e164)
    if stored and stored["otp"] == otp_code and stored["expires_at"] > datetime.now(timezone.utc):
        otp_store.pop(phone_number_e164, None) # Clear OTP after use
        return True
    return False


# --- Helper Functions (parse_mood_response remains the same) ---

def parse_mood_response(sms_body):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
        "\U0001F680-\U0001F6FF"  # Transport & Map Symbols
        "\U0001F1E0-\U0001F1FF"  # Regional Indicator Symbols (flags)
        "\U00002600-\U000027BF"  # Miscellaneous Symbols
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE 
    )

    # Use re.search() to find the first occurrence of an emoji anywhere in the string
    match = emoji_pattern.search(sms_body)

    detected_emoji = None
    if match:
        # .group(0) will return the entire matched emoji sequence (e.g., "😊", "👍", "🎉")
        # The `+` in the pattern ensures it can match sequences like skin tone modifiers
        # or multi-character emojis if they are composed of characters within the defined ranges.
        detected_emoji = match.group(0)
    full_text_response = sms_body

    return detected_emoji, full_text_response

# --- Routes ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('calendar_view'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('calendar_view'))

    if request.method == 'POST':
        if not db_firestore or not app_firebase_auth: # Check if Firebase is initialized
            flash('Application is not properly configured. Please contact support.', 'danger')
            return redirect(url_for('login'))

        phone_number_input = request.form.get('phone_number')
        # ... (phone number validation as before) ...
        formatted_phone_e164 = format_phone_to_e164(phone_number_input)
        if not formatted_phone_e164:
            flash('Invalid phone number format...', 'danger') # Keep full message
            return redirect(url_for('login'))

        # Generate and send OTP via Twilio (using our temporary store)
        otp = generate_and_store_otp(formatted_phone_e164)
        otp_message = (
            f"Your Mood Tracker verification code is: {otp}. "
            f"By verifying, you agree to receive daily SMS. Msg&Data rates may apply. Reply STOP to cancel."
        )
        if send_sms(formatted_phone_e164, otp_message):
            session['phone_for_verification'] = formatted_phone_e164
            flash(f'OTP sent to {formatted_phone_e164}. Please check your messages.', 'info')
            return redirect(url_for('verify_otp'))
        else:
            flash('Failed to send OTP...', 'danger') # Keep full message
            app.logger.error(f"Failed to send OTP to {formatted_phone_e164}")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for('calendar_view'))

    phone_for_verification = session.get('phone_for_verification')
    if not phone_for_verification:
        flash('Please provide your phone number first.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        otp_code = request.form.get('otp')

        if verify_stored_otp(phone_for_verification, otp_code):
            try:
                # OTP verified with our system. Now, get/create Firebase Auth user
                firebase_user_record = None
                try:
                    firebase_user_record = app_firebase_auth.get_user_by_phone_number(phone_for_verification)
                    app.logger.info(f"Firebase Auth: Found existing user {firebase_user_record.uid} for {phone_for_verification}")
                except firebase_auth.UserNotFoundError:
                    firebase_user_record = app_firebase_auth.create_user(phone_number=phone_for_verification)
                    app.logger.info(f"Firebase Auth: Created new user {firebase_user_record.uid} for {phone_for_verification}")

                user_uid = firebase_user_record.uid

                # Create/Update user profile in Firestore
                user_doc_ref = db_firestore.collection('users').document(user_uid)
                user_data_firestore = {
                    'phone_number': phone_for_verification,
                    'is_subscribed': True,
                    'consent_updated_at': firestore.SERVER_TIMESTAMP, # Use server timestamp
                }
                # Add created_at only if document doesn't exist (new user profile in Firestore)
                if not user_doc_ref.get().exists:
                    user_data_firestore['created_at'] = firestore.SERVER_TIMESTAMP

                user_doc_ref.set(user_data_firestore, merge=True) # merge=True to update if exists, create if not

                # Log in with Flask-Login using our FirebaseUser wrapper
                app_user = FirebaseUser.get(user_uid) # Fetch the newly created/updated user data
                if app_user:
                    login_user(app_user, remember=True)
                    session.pop('phone_for_verification', None)

                    welcome_message = "Welcome to Mood Tracker! You'll receive daily mood prompts. Reply STOP to unsubscribe."
                    send_sms(phone_for_verification, welcome_message)

                    flash('Successfully subscribed and logged in!', 'success')
                    return redirect(request.args.get('next') or url_for('calendar_view'))
                else:
                    flash('Login failed after OTP verification. Please try again.', 'danger')
                    app.logger.error(f"Failed to load FirebaseUser for UID {user_uid} after OTP verification.")

            except Exception as e:
                flash(f'An error occurred during Firebase user setup: {e}', 'danger')
                app.logger.error(f"Firebase setup error for {phone_for_verification}: {e}")
                # Consider what to do here. Maybe redirect to login or show a generic error.
                return redirect(url_for('login'))
        else:
            flash('Invalid OTP or OTP expired. Please try again.', 'danger')
            return redirect(url_for('verify_otp'))

    return render_template('verify_otp.html', phone_number=phone_for_verification)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/calendar')
@login_required
def calendar_view():
    if not current_user.is_subscribed: # current_user is now a FirebaseUser instance
        flash('You are not currently subscribed.', 'warning')

    entries_by_date_iso = {}
    try:
        # Firestore: Get mood entries for the current user
        # Entries are stored as subcollection: users/{uid}/mood_entries
        # Document ID in mood_entries can be YYYY-MM-DD
        entries_ref = db_firestore.collection('users').document(current_user.uid).collection('mood_entries')
        for entry_doc in entries_ref.stream():
            entry_data = entry_doc.to_dict()
            # Ensure entry_date is a string in YYYY-MM-DD. Firestore Timestamp needs conversion.
            entry_date_val = entry_data.get('entry_date')
            if isinstance(entry_date_val, datetime): # If Firestore Timestamp
                 entry_date_str = entry_date_val.strftime('%Y-%m-%d')
            elif isinstance(entry_date_val, str): # If already string
                 entry_date_str = entry_date_val
            else: # Fallback or error
                 entry_date_str = entry_doc.id # Assuming doc ID is YYYY-MM-DD

            entries_by_date_iso[entry_date_str] = {
                'emoji': entry_data.get('emoji'),
                'text_response': entry_data.get('text_response'),
                'entry_date': entry_date_str # Ensure this key exists for the template
            }
    except Exception as e:
        app.logger.error(f"Error fetching calendar entries for user {current_user.uid}: {e}")
        flash('Could not load calendar entries.', 'danger')

    return render_template('calendar.html', entries_by_date_iso=entries_by_date_iso, today_iso=date.today().isoformat())

# FOR TESTING ONLY
# @app.route('/calendar')
# # @login_required # STEP 1: Temporarily COMMENT OUT this line for testing without login
# def calendar_view():
#     # STEP 2: DEFINE THE TEST USER UID YOU USED IN FIRESTORE
#     # Replace "testUser123" with the actual Document ID you used for your test user in the 'users' collection.
#     TEST_USER_UID = "testUser123"

#     entries_by_date_iso = {}
#     active_uid_for_view = None # This will hold the UID whose data we're fetching

#     # Check if a real user is logged in
#     if current_user.is_authenticated and hasattr(current_user, 'uid'):
#         active_uid_for_view = current_user.uid
#         app.logger.info(f"Calendar view for logged-in user: {active_uid_for_view}")
#         if not getattr(current_user, 'is_subscribed', False): # Check if FirebaseUser has is_subscribed
#              flash('You are not currently subscribed to daily prompts.', 'warning')
#     else:
#         # No user logged in (because @login_required is commented out), so use the TEST_USER_UID
#         active_uid_for_view = TEST_USER_UID
#         app.logger.info(f"Calendar view for TEST user: {active_uid_for_view} (login bypassed for testing)")
#         flash(f"Displaying calendar for test user ({TEST_USER_UID}). Log in to see your personal calendar.", "info")

#     if not active_uid_for_view:
#         app.logger.error("Calendar view: Could not determine active UID.")
#         flash("Cannot display calendar: No user context available.", "danger")
#         # Render an empty calendar or redirect
#         return render_template('calendar.html', entries_by_date_iso={}, today_iso=date.today().isoformat())

#     try:
#         # Use active_uid_for_view to fetch data from Firestore
#         entries_ref = db_firestore.collection('users').document(active_uid_for_view).collection('mood_entries')
#        # app.logger.info(f"Fetching Firestore entries from path: {entries_ref.path}")
#         app.logger.info(f"Fetching Firestore entries from path: {entries_ref.parent.path}/{entries_ref.id}")

#         retrieved_entries_count = 0
#         for entry_doc in entries_ref.stream():
#             retrieved_entries_count += 1
#             entry_data = entry_doc.to_dict()
#             entry_date_val = entry_data.get('entry_date') # This is a Firestore Timestamp or a date string

#             entry_date_str = None
#             if isinstance(entry_date_val, datetime): # Firestore Timestamps are 'datetime' objects in Python Admin SDK
#                  entry_date_str = entry_date_val.strftime('%Y-%m-%d')
#             elif isinstance(entry_date_val, str): # If it was stored as an ISO string
#                  # You might want to validate its format here if necessary
#                  if re.match(r'^\d{4}-\d{2}-\d{2}$', entry_date_val):
#                     entry_date_str = entry_date_val
#                  else:
#                     app.logger.warning(f"Entry {entry_doc.id} has invalid string date format: {entry_date_val} for user {active_uid_for_view}")
#                     continue # Skip this entry
#             elif entry_date_val is None and entry_doc.id: # Fallback to document ID if entry_date field is missing
#                  if re.match(r'^\d{4}-\d{2}-\d{2}$', entry_doc.id): # Check if doc ID is YYYY-MM-DD
#                     entry_date_str = entry_doc.id
#                  else:
#                     app.logger.warning(f"Entry document ID {entry_doc.id} is not a valid date format for user {active_uid_for_view}")
#                     continue # Skip this entry
#             else:
#                 app.logger.warning(f"Entry {entry_doc.id} has unhandled entry_date type or missing doc_id for user {active_uid_for_view}. Data: {entry_data}")
#                 continue # Skip this entry

#             entries_by_date_iso[entry_date_str] = {
#                 'emoji': entry_data.get('emoji', '❓'), # Default emoji if missing
#                 'text_response': entry_data.get('text_response', ''), # Default text if missing
#                 'entry_date': entry_date_str # Ensure this is always populated for the template
#             }
        
#         if retrieved_entries_count == 0:
#             app.logger.info(f"No mood entries found for UID: {active_uid_for_view} at path: {entries_ref.path}")
#             # flash("No mood entries found for this period.", "info") # Optional: inform user
#         else:
#             app.logger.info(f"Successfully processed {len(entries_by_date_iso)} mood entries for UID: {active_uid_for_view}")

#     except Exception as e:
#         app.logger.error(f"Error fetching/processing calendar entries for UID {active_uid_for_view}: {e}", exc_info=True)
#         flash('Could not load calendar entries due to a server error.', 'danger')

#     return render_template('calendar.html', entries_by_date_iso=entries_by_date_iso, today_iso=date.today().isoformat())



@app.route('/api/mood_entry/<string:date_str>') # date_str is YYYY-MM-DD
@login_required
def get_mood_entry_details(date_str):
    try:
        # Firestore: Get mood entry for users/{uid}/mood_entries/{date_str}
        entry_doc_ref = db_firestore.collection('users').document(current_user.uid).collection('mood_entries').document(date_str)
        entry_doc = entry_doc_ref.get()
        if entry_doc.exists:
            entry_data = entry_doc.to_dict()
            return jsonify({
                'date': date_str, # Or entry_data.get('entry_date') if stored explicitly
                'emoji': entry_data.get('emoji'),
                'text_response': entry_data.get('text_response') or ""
            })
        return jsonify({'error': 'No entry found for this date'}), 404
    except Exception as e:
        app.logger.error(f"API error fetching mood entry for user {current_user.uid}, date {date_str}: {e}")
        return jsonify({'error': f'Could not load mood details: {e}'}), 500


# FOR TESTING ONLY
# @app.route('/api/mood_entry/<string:date_str>') # date_str is YYYY-MM-DD
# def get_mood_entry_details(date_str):
#     current_user.uid = "testUser123"
#     try:
#         # Firestore: Get mood entry for users/{uid}/mood_entries/{date_str}
#         entry_doc_ref = db_firestore.collection('users').document(current_user.uid).collection('mood_entries').document(date_str)
#         entry_doc = entry_doc_ref.get()
#         if entry_doc.exists:
#             entry_data = entry_doc.to_dict()
#             return jsonify({
#                 'date': entry_data.get('entry_date'),
#                 'emoji': entry_data.get('emoji'),
#                 'text_response': entry_data.get('text_response') or ""
#             })
#         return jsonify({'error': 'No entry found for this date'}), 404
#     except Exception as e:
#         app.logger.error(f"API error fetching mood entry for user {current_user.uid}, date {date_str}: {e}")
#         return jsonify({'error': f'Could not load mood details: {e}'}), 500



# --- Twilio Webhook for Incoming SMS ---
@app.route('/sms/receive', methods=['POST'])
def sms_receive():
    app.logger.info("Recieved SMS")
    if not db_firestore or not app_firebase_auth:
        app.logger.error("Webhook /sms/receive: Firebase not initialized.")
        return "Error: Service not configured", 500

    from_number_raw = request.values.get('From', None)
    sms_body_original = request.values.get('Body', "") # Keep original for parsing
    sms_body_upper = sms_body_original.strip().upper()

    # ... (phone number validation as before) ...
    from_number_e164 = format_phone_to_e164(from_number_raw)
    if not from_number_e164: # ... (error handling as before) ...
        return "Error: Invalid 'From' number format", 400

    # Get Firebase Auth user by phone
    try:
        firebase_user_record = app_firebase_auth.get_user_by_phone_number(from_number_e164)
        user_uid = firebase_user_record.uid
        print(user_uid)
        user_doc_ref = db_firestore.collection('users').document(user_uid)
        user_profile = user_doc_ref.get().to_dict() or {} # Get existing profile or empty dict
        print(user_profile)
    except firebase_auth.UserNotFoundError:
        app.logger.info(f"Webhook /sms/receive: SMS from phone {from_number_e164} not linked to any Firebase Auth user.")
        # Optionally, create user here or send a "please sign up" message
        return "User not registered in Firebase Auth", 200
    except Exception as e:
        app.logger.error(f"Webhook /sms/receive: Error fetching Firebase user for {from_number_e164}: {e}")
        return "Error: Could not process user", 500

    # Handle STOP, START keywords
    if sms_body_upper == "STOP":
        user_doc_ref.update({'is_subscribed': False, 'consent_updated_at': firestore.SERVER_TIMESTAMP})
        app.logger.info(f"User {user_uid} ({from_number_e164}) opted out (STOP).")
        return '', 204

    if sms_body_upper == "START":
        user_doc_ref.update({'is_subscribed': True, 'consent_updated_at': firestore.SERVER_TIMESTAMP})
        app.logger.info(f"User {user_uid} ({from_number_e164}) opted in (START).")
        return '', 204

    if not user_profile.get('is_subscribed', False):
        app.logger.info(f"User {user_uid} ({from_number_e164}) sent message but is not subscribed. Ignoring.")
        return "User not subscribed", 200

    emoji, text_content = parse_mood_response(sms_body_original)
    if not emoji: # default emoji if no emoji is attached
        app.logger.info(f"No emoji provided. Using default emoji")
        emoji = "♠️"

    # Save mood entry to Firestore: users/{uid}/mood_entries/{YYYY-MM-DD}
    entry_date_str = date.today().isoformat()
    mood_entry_ref = user_doc_ref.collection('mood_entries').document(entry_date_str)
    mood_data = {
        'entry_date': datetime.now(timezone.utc),
        'emoji': emoji,
        'text_response': text_content,
        'timestamp': datetime.now(timezone.utc)
    }
    mood_entry_ref.set(mood_data) # Overwrites if entry for today already exists
    app.logger.info(f"Webhook /sms/receive: Logged mood for user {user_uid} on {entry_date_str}")
    return '', 204


# --- APScheduler Setup for Daily SMS ---
def scheduled_daily_prompt_job():
    if not db_firestore:
        app.logger.error("Scheduler: Firestore not initialized. Skipping job.")
        return

    with app.app_context(): # Still useful for Flask context, though not strictly needed for Firestore
        try:
            users_ref = db_firestore.collection('users').where('is_subscribed', '==', True)
            subscribed_users_docs = users_ref.stream()

            count = 0
            for user_doc in subscribed_users_docs:
                user_data = user_doc.to_dict()
                phone_number = user_data.get('phone_number')
                if phone_number:
                    app.logger.info(f"Scheduler: Sending daily prompt to {phone_number} (User ID: {user_doc.id})")
                    send_daily_mood_prompt_sms(phone_number)
                    count += 1
            app.logger.info(f"Scheduler: Sent daily prompts to {count} subscribed user(s).")
            if count == 0:
                 app.logger.info("Scheduler: No subscribed users found to send daily prompts.")
        except Exception as e:
            app.logger.error(f"Scheduler: Error fetching subscribed users: {e}")

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(scheduled_daily_prompt_job, 'cron', hour=12, minute=58)

# --- Flask CLI Commands ---
@app.cli.command("init-db") # This command is now a misnomer, as there's no SQL DB to init tables for.
                            # Could be removed or repurposed for other Firebase setup tasks if any.
def init_db_command():
    click.echo("Database is Firestore. No table initialization needed via this command.")
    click.echo("Ensure your Firebase project is set up and GOOGLE_APPLICATION_CREDENTIALS points to your service account key.")

@app.cli.command("test-prompt")
@click.option('--phone', required=True, help='Phone number (E.164) to send test prompt.')
def test_prompt_command(phone):
    if not db_firestore or not app_firebase_auth:
        click.echo("Firebase not initialized. Cannot test prompt.", err=True)
        return
    try:
        firebase_user_record = app_firebase_auth.get_user_by_phone_number(phone)
        user_uid = firebase_user_record.uid
        user_doc = db_firestore.collection('users').document(user_uid).get()
        if user_doc.exists and user_doc.to_dict().get('is_subscribed'):
            if send_daily_mood_prompt_sms(phone):
                click.echo(f"Test prompt sent to subscribed user {phone}")
            else:
                click.echo(f"Failed to send test prompt to {phone}.", err=True)
        else:
            click.echo(f"User {phone} not found or not subscribed in Firestore.", err=True)
    except firebase_auth.UserNotFoundError:
        click.echo(f"User with phone {phone} not found in Firebase Auth.", err=True)
    except Exception as e:
        click.echo(f"Error during test-prompt: {e}", err=True)


# --- Main Execution Block ---
if __name__ == '__main__':
    # db.create_all() # REMOVE SQLAlchemy specific call

    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        if not scheduler.running: # Check if Firebase was initialized before starting scheduler
            if db_firestore:
                scheduler.start()
                app.logger.info("APScheduler started for daily prompts.")
            else:
                app.logger.error("APScheduler not started because Firebase is not initialized.")
        else:
            app.logger.info("APScheduler already running.")
    else:
        app.logger.info("APScheduler not started in this Flask reloader process.")

    serve(app, host="0.0.0.0", port=5000)