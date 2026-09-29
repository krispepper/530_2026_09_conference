from flask import Flask, redirect, render_template, request, session, url_for
from mysql.connector import Error, IntegrityError
from werkzeug.routing import BuildError

from db_seeder import DefaultConferenceSeeder
from conference import (
    create_conference,
    get_conference_by_id,
    get_conference_for_organizer,
    get_my_conferences,
    get_published_conferences,
    publish_conference,
    validate_conference_form,
)
from participant_conf import (
    get_participant_conference_status,
    invite_participant,
    register_participant,
    unregister_participant,
)

from queries import *
from user import *
import os
from dotenv import load_dotenv, dotenv_values

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
    return render_template('index.html')


@app.context_processor
def navigation_context():
    user_id = session.get('user_id')
    current_user = get_user_by_id(user_id) if user_id else None
    return {
        'current_user': current_user,
        'can_manage_conferences': bool(
            current_user and (
                current_user.is_organizer or current_user.is_admin
            )
        ),
    }


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None)

    user_id = request.form.get('user_id', '').strip()
    if not user_id:
        return render_template(
            'login.html', error='Enter a user ID.'
        ), 400

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


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/add_user', methods=['POST'])
def add_user():
    fields = ['user_id', 'f_name', 'l_name', 'email', 'is_participant', 'is_admin', 'is_organizer']
    values = [(request.form[f] if not f.startswith("is_") else (f in request.form)) for f in
              fields]  # [request.form[f] for f in fields]
    print(values)
    try:
        create_user(*values)
        # session.clear() #clear session on add user
        # session['user_id'] = values[0] #user_id
    except IntegrityError:
        print("User already exists.")
        # TODO: notify client

    return render_template('view_user.html', dat=get_user_by_id(values[0]).__dict__)


@app.route('/add_user', methods=['GET'])
def add_user_page():
    return render_template('add_user.html')


@app.route('/view_user/<user_id>', methods=['GET'])
def view_user_page(**kwargs):
    return render_template('view_user.html', dat=get_user_by_id(request.view_args['user_id']).__dict__)


@app.route('/conferences', methods=['GET'])
def conferences_page():
    return render_template(
        'conferences.html',
        conferences=get_published_conferences(),
    )


@app.route('/my-conferences', methods=['GET'])
def my_conferences_page():
    user_id = session.get('user_id')
    if not user_id:
        return 'Login required.', 401
    user = get_user_by_id(user_id)
    if not user or not (user.is_organizer or user.is_admin or user.is_participant):
        return 'Organizer or participant privileges required.', 403
    is_conference_owner = user.is_organizer or user.is_admin
    return render_template(
        'conferences.html',
        title='My Conferences',
        conferences=get_my_conferences(user_id, is_conference_owner),
        show_status=True,
    )


@app.route('/conferences/new', methods=['GET'])
def create_conference_page():
    if not session.get('user_id') or not (
        is_user_organizer(session['user_id'])
        or is_user_admin(session['user_id'])
    ):
        return 'Organizer privileges required.', 403
    return render_template('create_conference.html', values={}, errors={})


@app.route('/conferences', methods=['POST'])
def create_conference_route():
    organizer_id = session.get('user_id')
    if not organizer_id or not (
        is_user_organizer(organizer_id) or is_user_admin(organizer_id)
    ):
        return 'Organizer privileges required.', 403

    values, errors = validate_conference_form(request.form)
    if errors:
        return render_template(
            'create_conference.html', values=request.form, errors=errors
        ), 400

    try:
        conference_id = create_conference(organizer_id, **values)
    except Error:
        app.logger.exception("Unable to save conference")
        return render_template(
            'create_conference.html',
            values=request.form,
            errors={"form": "The conference could not be saved. Please try again."},
        ), 500

    return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<conference_id>/publish', methods=['POST'])
def publish_conference_route(conference_id):
    organizer_id = session.get('user_id')
    if not organizer_id or not (
        is_user_organizer(organizer_id) or is_user_admin(organizer_id)
    ):
        return 'Organizer privileges required.', 403

    try:
        publish_conference(conference_id, organizer_id)
    except ValueError:
        return 'Conference was not found or is already published.', 404
    except Error:
        app.logger.exception("Unable to publish conference")
        return 'The conference could not be published. Please try again.', 500

    return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<conference_id>', methods=['GET'])
def conference_page(conference_id):
    conference = get_conference_by_id(
        conference_id, session.get('user_id')
    )
    if conference is None and session.get('user_id'):
        conference = get_conference_for_organizer(
            conference_id, session['user_id']
        )
    if conference is None:
        return 'Conference not found.', 404
    if session.get('user_id'):
        conference.membership_status = get_participant_conference_status(
            session['user_id'], conference_id
        )
    return render_template(
        'conference.html',
        conference=conference,
        is_owner=conference.organizer_id == session.get('user_id'),
    )


@app.route('/conferences/<conference_id>/invite', methods=['POST'])
def invite_participant_route(conference_id):
    organizer_id = session.get('user_id')
    if not organizer_id or not (
        is_user_organizer(organizer_id) or is_user_admin(organizer_id)
    ):
        return 'Organizer privileges required.', 403

    participant_id = request.form.get('participant_id', '').strip()
    if not participant_id:
        return 'Participant ID is required.', 400

    try:
        invite_participant(participant_id, conference_id, organizer_id)
    except ValueError as error:
        return str(error), 404
    except Error:
        app.logger.exception("Unable to send conference invitation")
        return 'The invitation could not be sent. Please try again.', 500

    return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<conference_id>/register', methods=['POST'])
def register_participant_route(conference_id):
    participant_id = session.get('user_id')
    if not participant_id:
        return 'Login required.', 401
    try:
        register_participant(participant_id, conference_id)
    except PermissionError as error:
        return str(error), 403
    except ValueError as error:
        return str(error), 404
    except Error:
        app.logger.exception("Unable to register participant")
        return 'Registration failed. Please try again.', 500
    return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<conference_id>/unregister', methods=['POST'])
def unregister_participant_route(conference_id):
    participant_id = session.get('user_id')
    if not participant_id:
        return 'Login required.', 401
    try:
        unregister_participant(participant_id, conference_id)
    except ValueError as error:
        return str(error), 400
    except Error:
        app.logger.exception("Unable to unregister participant")
        return 'Unregistration failed. Please try again.', 500
    return redirect(url_for('my_conferences_page'))


if __name__ == '__main__':
    if RESET_ON_STARTUP:
        reset_tables()

    create_databases()
    create_tables()
    DefaultConferenceSeeder.initialize_db()
    app.run(debug=True, port=int(PORT) if PORT else 5000)
