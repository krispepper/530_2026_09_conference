#!/bin/bash

if [ ! -d "./src/venv" ] 
then
    python3 -m venv ./src/venv
fi

source ./src/venv/bin/activate

pip install flask

# pip install mysql-connector-python
