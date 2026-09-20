#!/bin/bash

if [ ! -d "./.venv" ] 
then
    python3 -m venv ./.venv
fi

source ./.venv/bin/activate

# pip install flask

# pip install mysql-connector-python

pip install -r requirements.txt
