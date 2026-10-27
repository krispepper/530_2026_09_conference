# AI assistance: ChatGPT helped remove duplicate conference lookups and restore access error handling.
# AI assistance: ChatGPT helped add the past events route.
from past_attendance import get_past_events

# Purpose: Handle website routes and user sessions.
# AI assistance: ChatGPT helped connect conference seat counts.
# Author: Priya

import csv
import io

from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from mysql.connector import Error, IntegrityError, errorcode
from mysql.connector import Error as DBError
from werkzeug.routing import BuildError

from db import reset_tables, RESET_ON_STARTUP, create_databases, create_tables
from conference import (
    attach_seat_availability,
    create_conference,
    get_conference_by_id,
    get_conference_for_admin,
    get_conference_for_organizer,
    get_my_conferences,
    get_published_conferences,
    publish_conference,
    validate_conference_form,
)
from db_seeder import DBSeeder
from participant_conf import (
    get_participant_conference_status,
    get_conference_participants,
    invite_participant,
    register_participant,
    unregister_participant,
    get_participant_upcoming_attendance,
    get_all_upcoming_attendance,
    get_registration_receipt,
)

from user import *
import os
from dotenv import load_dotenv, dotenv_values
from audit_log import fetch_conference_log

from datetime import datetime

load_dotenv()

# export PORT="[server port]"
PORT = os.getenv("PORT")

app = Flask(__name__)

IS_PROD = os.getenv("IS_PROD", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SECRET_KEY = os.getenv("FLASK_SECRET_KEY_PROD") if IS_PROD else os.getenv("FLASK_SECRET_KEY_DEV")
app.config["SECRET_KEY"] = SECRET_KEY


@app.route('/', methods=['GET'])
def get_index():
    """Render the application landing page."""
    return render_template('index.html')


@app.context_processor
def navigation_context():
    """Provide the current user and navigation permissions to templates."""
    user_id = session.get('user_id')
    try:
        current_user = get_user_by_id(user_id) if user_id else None
    except DBError:
        current_user = None
        user_id = None
    return {
        'current_user': current_user,
        'logged_in': bool(user_id),
        'can_manage_conferences': bool(
            current_user and (
                current_user.is_organizer or current_user.is_admin
            )
        ),
        'is_admin': bool(current_user and current_user.is_admin),
        'can_manage_users': bool(current_user and current_user.is_admin),
    }


def get_current_user():
    """Load the authenticated user for backend authorization checks."""
    user_id = session.get('user_id')
    return get_user_by_id(user_id) if user_id else None


def require_role(*roles):
    """Return an HTTP error response unless the session has one of the roles."""
    user = get_current_user()
    if user is None:
        return None, ('Login required.', 401)
    if user.is_admin:
        return user, None
    if not any(getattr(user, role, False) for role in roles):
        return None, ('Access denied.', 403)
    return user, None


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Render the login page or authenticate a user and start a session."""
    if request.method == 'GET':
        return render_template('login.html', error=None)

    user_id = request.form.get('user_id', '').strip()
    if not user_id:
        return render_template(
            'login.html', error='Enter a user ID.'
        ), 400

    try:
        user = get_user_by_id(user_id)
        if user is None:
            return render_template(
                'login.html', error='User ID was not found.'
            ), 401

        session.clear()
        session['user_id'] = user.user_id
        try:
            return redirect(url_for('create_conference_page') if user.is_organizer
                            else url_for('conferences_page'))
        except BuildError:
            return render_template(
                'login.html', error='Unable to complete login right now.'
            ), 500
    except DBError as err:
        return render_template('server_error.html', errno=err.errno), 500


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Clear the current session and redirect to the login page."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/add_user', methods=['POST'])
def add_user():
    """Create a user from submitted form data and display the user profile."""
    _, error = require_role('is_admin')
    if error:
        return error
    fields = ['user_id', 'f_name', 'l_name', 'email', 'is_participant', 'is_admin', 'is_organizer']
    values = [(request.form[f] if not f.startswith("is_") else (f in request.form)) for f in
              fields]  # [request.form[f] for f in fields]
    try:
        create_user(*values)
    except ValueError as error:
        return render_template(
            'add_user.html', error=str(error)
        ), 400
    except IntegrityError:
        return render_template(
            'add_user.html', error='User ID already exists.'
        ), 409
    except DBError as err:
        return render_template('server_error.html', errno=err.errno), 500

    try:
        return render_template('view_user.html', dat=get_user_by_id(values[0]).__dict__)
    except DBError as err:
        return render_template('server_error.html', errno=err.errno), 500


@app.route('/add_user', methods=['GET'])
def add_user_page():
    """Render the new-user form."""
    _, error = require_role('is_admin')
    if error:
        return error
    return render_template('add_user.html')


@app.route('/view_user/<user_id>', methods=['GET'])
def view_user_page(**kwargs):
    """Render the profile page for the requested user."""
    try:
        user, error = require_role('is_admin')
        requested_id = request.view_args['user_id']
        if error and (get_current_user() is None or get_current_user().user_id != requested_id):
            return error
        requested_user = get_user_by_id(requested_id)
        if requested_user is None:
            return 'User not found.', 404
        return render_template('view_user.html', dat=requested_user.__dict__)
    except DBError as err:
        return render_template('server_error.html', errno=err.errno), 500


@app.route('/conferences', methods=['GET'])
def conferences_page():
    """Render the list of published open conferences."""
    user_id = session.get('user_id')
    try:
        user = get_user_by_id(user_id) if user_id else None
        organizer_id = (
            user.user_id
            if user and (user.is_organizer or user.is_admin)
            else None
        )
        return render_template(
            'conferences.html',
            conferences=attach_seat_availability(
                get_published_conferences(organizer_id)
            ),
        )
    except DBError as err:
        return render_template('server_error.html', errno=err.errno), 500


@app.route('/my-conferences', methods=['GET'])
def my_conferences_page():
    """Render conferences owned by or associated with the signed-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return 'Login required.', 401
    try:
        user = get_user_by_id(user_id)
        if not user or not (user.is_organizer or user.is_admin or user.is_participant):
            return 'Organizer or participant privileges required.', 403
        is_conference_owner = user.is_organizer or user.is_admin
        return render_template(
            'conferences.html',
            title='My Conferences',
            conferences=attach_seat_availability(
                get_my_conferences(
                    user_id,
                    is_conference_owner,
                    is_admin=user.is_admin,
                )
            ),
            show_status=True,
        )
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500
    


@app.route('/my-conferences/past', methods=['GET'])
def past_events_page():
    """Show past events only for the signed-in participant."""
    user_id = session.get('user_id')
    if not user_id:
        return 'Login required.', 401

    try:
        user = get_user_by_id(user_id)
        if not user or not user.is_participant:
            return 'Participant privileges required.', 403

        return render_template(
            'past_events.html',
            events=get_past_events(user_id),
        )
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500


@app.route('/conferences/new', methods=['GET'])
def create_conference_page():
    """Render the conference creation form for an organizer or admin."""
    try:
        if not session.get('user_id') or not (
            is_user_organizer(session['user_id'])
            or is_user_admin(session['user_id'])
        ):
            return 'Organizer privileges required.', 403
        return render_template('create_conference.html', values={}, errors={})
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500


@app.route('/conferences', methods=['POST'])
def create_conference_route():
    """Create a new conference."""
    organizer_id = session.get('user_id')
    try: 
        if not organizer_id or not (
            is_user_organizer(organizer_id) or is_user_admin(organizer_id)
        ):
            return 'Organizer privileges required.', 403
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500

    values, errors = validate_conference_form(request.form)
    if errors:
        return render_template(
            'create_conference.html', values=request.form, errors=errors
        ), 400

    try:
        conference_id = create_conference(organizer_id, **values)
    except Error as err:
        app.logger.exception("Unable to save conference")
        return render_template(
            'create_conference.html',
            values=request.form,
            errors={"form": f"The conference could not be saved. Please try again. Error code: {err.errno}"},
        ), 500

    return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<conference_id>/publish', methods=['POST'])
def publish_conference_route(conference_id):
    """Publish a conference owned by the signed-in organizer or admin."""
    organizer_id = session.get('user_id')
    if not organizer_id or not (
        is_user_organizer(organizer_id) or is_user_admin(organizer_id)
    ):
        return 'Organizer privileges required.', 403

    user = get_user_by_id(organizer_id)
    try:
        publish_conference(conference_id, organizer_id, is_admin=user.is_admin)
    except ValueError:
        return 'Conference was not found or is already published.', 404
    except Error as err:
        app.logger.exception("Unable to publish conference")
        return f'The conference could not be published. Please try again. Error Code: {err.errno}', 500

    return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<conference_id>', methods=['GET'])
def conference_page(conference_id):
    """Render a conference when the current user has access to it."""
    try:
        conference = get_conference_by_id(
            conference_id, session.get('user_id')
        )
        if conference is None and session.get('user_id'):
            user = get_user_by_id(session['user_id'])
            if user and user.is_admin:
                conference = get_conference_for_admin(conference_id)
            elif user and user.is_organizer:
                conference = get_conference_for_organizer(
                    conference_id, session['user_id']
                )

        if conference is None:
            existing_conference = get_conference_for_admin(conference_id)
            if existing_conference is not None:
                if not session.get('user_id'):
                    return 'Login required.', 401
                return 'You do not have permission to access this conference.', 403
            return 'Conference not found.', 404

        attach_seat_availability([conference])
        if session.get('user_id'):
            conference.membership_status = get_participant_conference_status(
                session['user_id'], conference_id
            )
        can_manage = bool(
            current_user := get_current_user()
        ) and (
            current_user.is_admin
            or conference.organizer_id == current_user.user_id
        )
        return render_template(
            'conference.html',
            conference=conference,
            is_owner=can_manage,
        )
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500


@app.route('/conferences/<conference_id>/participants.csv', methods=['GET'])
def export_participants_route(conference_id):
    """Download participant data for a conference as a CSV file."""
    user_id = session.get('user_id')
    if not user_id:
        return 'Login required.', 401

    try: 
        user = get_user_by_id(user_id)
        if not user or not (user.is_organizer or user.is_admin):
            return 'Organizer privileges required.', 403

        conference = (
            get_conference_for_admin(conference_id)
            if user.is_admin
            else get_conference_for_organizer(conference_id, user_id)
        )
        if conference is None:
            return 'Conference not found.', 404
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500

    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow([
        'participant_id',
        'first_name',
        'last_name',
        'email',
        'status',
        'invited_at',
        'registered_at',
    ])
    try:
        writer.writerows(get_conference_participants(conference_id))
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500

    filename = f"participants-{conference.conference_id}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Cache-Control': 'no-store',
        },
    )


@app.route('/delete_user/<user_id>', methods=['POST'])
def delete_user(user_id):
    _, error = require_role('is_admin')
    if error:
        return error
    try:
        delete_user_by_id(user_id)
        return "User deleted successfully"
    except Error as err:
        app.logger.exception(f"Unable to delete user. Error code: {err.errno}")
        return f"Unable to delete user. Database error: {err.errno}", 500
    except Exception as e:
        return f"Error deleting user: {e}"

@app.route('/cancel_registration/<conference_id>/<user_id>', methods=['DELETE'])
def cancel_reg_route(conference_id, user_id):
    current_user, error = require_role('is_participant', 'is_admin')
    if error:
        return jsonify({"error": error[0]}), error[1]
    if not current_user.is_admin and current_user.user_id != user_id:
        return jsonify({"error": "You can only cancel your own registration."}), 403
    try:
        cancel_registration(user_id, conference_id)
        return jsonify({"message": "Registration cancelled"}), 200
    except (ValueError, PermissionError) as error:
        return jsonify({"error": str(error)}), 400
    except Error as err:
        app.logger.exception(f"Unable to cancel registration. Error code: {err.errno}")
        return jsonify({"error": f"Unable to cancel registration. Database error: {err.errno}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 400


#TODO: Add a route for inviting participants to a open conference case?
# This should only be accessible to organizers and admins!
@app.route('/conferences/<conference_id>/invite', methods=['POST'])
def invite_participant_route(conference_id):
    """Invite a participant to a restricted conference."""
    try:
        user, error = require_role('is_organizer', 'is_admin')
        if error:
            return error
        organizer_id = user.user_id

        participant_id = request.form.get('participant_id', '').strip()
        if not participant_id:
            return 'Participant ID is required.', 400

        invite_participant(
            participant_id,
            conference_id,
            organizer_id,
            is_admin=user.is_admin,
        )
    except ValueError as error:
        return str(error), 404
    except Error as err:
        app.logger.exception(f"Unable to send conference invitation. Code: {err.errno}")
        return f'The invitation could not be sent. Please try again. Error code: {err.errno}', 500

    return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<conference_id>/register', methods=['POST'])
def register_participant_route(conference_id):
    """Register the signed-in user for a conference."""
    participant_id = session.get('user_id')
    user, error = require_role('is_participant', 'is_admin')
    if error:
        return error
    try:
        register_participant(
            participant_id,
            conference_id,
            is_admin=user.is_admin,
        )
    except PermissionError as error:
        return str(error), 403
    except ValueError as error:
        return str(error), 404
    except Error as err:
        app.logger.exception(f"Unable to register participant. Code: {err.errno}")
        return f'Registration failed. Please try again. Error code: {err.errno}', 500
    return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<conference_id>/unregister', methods=['POST'])
def unregister_participant_route(conference_id):
    """Remove the signed-in participant from a registered conference."""
    participant_id = session.get('user_id')
    _, error = require_role('is_participant', 'is_admin')
    if error:
        return error
    try:
        unregister_participant(participant_id, conference_id)
    except ValueError as error:
        return str(error), 400
    except Error as err:
        app.logger.exception(f"Unable to unregister participant. Code: {err.errno}")
        return f'Unregistration failed. Please try again. Error code: {err.errno}', 500
    return redirect(url_for('my_conferences_page'))


@app.route('/conferences/<conference_id>/receipt', methods=['GET'])
def download_registration_receipt(conference_id):
    """Download the signed-in participant's receipt for a registered conference."""
    user, error = require_role('is_participant', 'is_admin')
    if error:
        return error
    participant_id = user.user_id

    try:
        receipt = get_registration_receipt(participant_id, conference_id)
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500
    if receipt is None:
        return 'No registration was found.', 404

    first_name, last_name, registration_number, registered_at, name, event_datetime, location, description = receipt
    submission_date = (
        registered_at.strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(registered_at, 'strftime')
        else str(registered_at)
    )
    event_date = (
        event_datetime.strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(event_datetime, 'strftime')
        else str(event_datetime)
    )
    receipt_text = "\n".join([
        "Conference Registration Receipt",
        "",
        f"Participant: {first_name} {last_name}",
        f"Registration number: {registration_number}",
        f"Submission date: {submission_date}",
        "",
        "Selected session:",
        f"  {name}",
        "",
        "Current session details:",
        f"  Date and time: {event_date}",
        f"  Location: {location}",
        f"  Description: {description}",
    ]) + "\n"

    return Response(
        receipt_text,
        mimetype='text/plain',
        headers={
            'Content-Disposition': (
                f'attachment; filename="registration-{registration_number}.txt"'
            ),
            'Cache-Control': 'no-store',
        },
    )

@app.route('/conference_audit', methods=['GET'])
def view_audit_log():
    try:
        user, error = require_role('is_organizer', 'is_admin')
        if error:
            return error

        before_time = datetime.fromisoformat(request.args.get("before")) if "before" in request.args else None
        after_time = datetime.fromisoformat(request.args.get("after")) if "after" in request.args else None

        log = fetch_conference_log(
            request.args.get("conference"),
            request.args.get("user"),
            request.args.get("action"),
            before_time,
            after_time,
            owner_id=None if user.is_admin else user.user_id,
        )
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500

    return render_template(
        'audit_log.html',
        log=log,
        no_results=(len(log)==0)
    )

@app.route('/upcoming_attendance', methods=['GET'])
def view_upcoming_attendance():
    try:
        user, error = require_role('is_participant', 'is_admin')
        if error:
            return error

        upcoming = (
            get_all_upcoming_attendance()
            if user.is_admin
            else get_participant_upcoming_attendance(user.user_id)
        )
    except Error as err:
        return render_template('server_error.html', errno=err.errno), 500

    return render_template(
        'upcoming_attendance.html',
        upcoming=upcoming,
        no_results=(len(upcoming)==0)
    )

if __name__ == '__main__':
    """Entry point for the application."""
    try:
        if RESET_ON_STARTUP:
            reset_tables()

        # Create testing DB if not in production.
        # Otherwise, assume the production DB already exists and is managed externally. (compsci server)
    
        if not IS_PROD:
            create_databases()

        create_tables()
        DBSeeder.initialize_db()
    except Error as err:
        print(f"Database error: {err.errno}")
        print(err)
    app.run(debug=True, port=int(PORT) if PORT else 5000)
