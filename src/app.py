from flask import Flask, render_template, request
from mysql.connector import IntegrityError

from queries import *
from user import *
import os
from dotenv import load_dotenv, dotenv_values
load_dotenv()

# export PORT="[server port]"
PORT = os.getenv("PORT")


app = Flask(__name__)

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
   finally:
      return render_template('view_user.html', dat = get_user_by_id(values[0]).__dict__)

@app.route('/add_user', methods=['GET'])
def add_user_page():
   return render_template('add_user.html')

@app.route('/view_user/<user_id>', methods=['GET'])
def view_user_page(**kwargs):
   return render_template('view_user.html', dat = get_user_by_id(request.view_args['user_id']).__dict__)

if __name__ == '__main__':
    app.run(debug=True, port = PORT)
