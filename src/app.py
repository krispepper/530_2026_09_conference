#!./.venv/bin/python3

from flask import Flask, redirect, render_template, request, session, url_for
from mysql.connector import Error, IntegrityError

from conference import (
    create_conference,
    get_conference_by_id,
    get_conference_for_organizer,
    get_published_conferences,
    publish_conference,
    validate_conference_form,
)
from queries import *
from user import *
# importing os module for environment variables
import os
# importing necessary functions from dotenv library
from dotenv import load_dotenv, dotenv_values 
# loading variables from .env file
load_dotenv() 
# export PORT="[server port]"
PORT = os.getenv("PORT")

#print("Hello world!")


app = Flask(__name__)
IS_PROD = os.getenv("IS_PROD", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SECRET_KEY = os.getenv("FLASK_SECRET_KEY_PROD") if IS_PROD else os.getenv("FLASK_SECRET_KEY_DEV")
app.config["SECRET_KEY"] = os.getenv(SECRET_KEY, "null")

@app.route('/', methods=['GET'])
def get_index():
   test_data = get_test()
   return render_template('index.html', test_data = test_data)

@app.route('/add_user', methods=['POST'])
def add_user():
   fields = ['user_id', 'f_name', 'l_name', 'email', 'is_participant', 'is_admin', 'is_organizer']
   values = [(request.form[f] if not f.startswith("is_") else (f in request.form)) for f in fields]#[request.form[f] for f in fields]
   print(values)
   try:
      create_user(*values)
   except IntegrityError:
      print("User already exists.")
      # TODO: notify client
   return render_template('view_user.html', dat = get_user_by_id(values[0]).__dict__)

@app.route('/add_user', methods=['GET'])
def add_user_page():
   return render_template('add_user.html')

@app.route('/view_user/<user_id>', methods=['GET'])
def view_user_page(**kwargs):
   return render_template('view_user.html', dat = get_user_by_id(request.view_args['user_id']).__dict__)


@app.route('/conferences', methods=['GET'])
def conferences_page():
   return render_template(
       'conferences.html',
       conferences=get_published_conferences(),
   )


@app.route('/conferences/new', methods=['GET'])
def create_conference_page():
   if not session.get('user_id') or not is_user_organizer(session['user_id']):
      return 'Organizer privileges required.', 403
   return render_template('create_conference.html', values={}, errors={})


@app.route('/conferences', methods=['POST'])
def create_conference_route():
   organizer_id = session.get('user_id')
   if not organizer_id or not is_user_organizer(organizer_id):
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


@app.route('/conferences/<int:conference_id>/publish', methods=['POST'])
def publish_conference_route(conference_id):
   organizer_id = session.get('user_id')
   if not organizer_id or not is_user_organizer(organizer_id):
      return 'Organizer privileges required.', 403

   try:
      publish_conference(conference_id, organizer_id)
   except ValueError:
      return 'Conference was not found or is already published.', 404
   except Error:
      app.logger.exception("Unable to publish conference")
      return 'The conference could not be published. Please try again.', 500

   return redirect(url_for('conference_page', conference_id=conference_id))


@app.route('/conferences/<int:conference_id>', methods=['GET'])
def conference_page(conference_id):
   conference = get_conference_by_id(conference_id)
   if conference is None and session.get('user_id'):
      conference = get_conference_for_organizer(
          conference_id, session['user_id']
      )
   if conference is None:
      return 'Conference not found.', 404
   return render_template(
       'conference.html',
       conference=conference,
       is_owner=conference.organizer_id == session.get('user_id'),
   )

#TODO: view conferences list view...


if __name__ == '__main__':
    app.run(debug=True, port=int(PORT) if PORT else 5000)
