#!./venv/bin/python3

from flask import Flask, render_template, request
from queries import *


#print("Hello world!")


app = Flask(__name__)

@app.route('/', methods=['GET'])
def get_index():
   test_data = get_test()
   return render_template('index.html', test_data = test_data)


if __name__ == '__main__':
    app.run(debug=True)
