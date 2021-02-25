# TPPT dry run

## General

This is documentation for running TPPT Analysis in dry run environment which basically just means running the software in source code form in Python interpreter.

## Setup

The dry run environment is delivered in source form and is hence not directly executable. Python needs to be installed on the system and the system needs to have internet access to access the general pypi server.

### Windows

Install Python 3.9.1. Other versions might also work but have not been tested.

To set things up, open console (cmd.exe) in TPPT Analysis root directory. Then type

    python -m venv venv

This will create a Python virtual environment in local directory `venv`.

Then type following

    venv\Scripts\Activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt

Now the virtual environment is setup for running TPPT Analysis.

### Linux

Install Python 3.6.8. This seems to be installed by default in Ubuntu 18.04 LTS. Install `venv` and `pip`:

sudo apt install python3-venv
sudo apt install python3-pip

To set things up, open terminal in TPPT Analysis root directory. Then type

    python3 -m venv venv

This will create a Python virtual environment in local directory `venv`.

Then type following

    source venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt

Now the virtual environment is setup for running TPPT Analysis.

## running TPPT Analysis

Open terminal in TPPT Analysis root directory and activate the Python virtual environment. Then execute commmand

    python main.py --database=/home/foo/tppt/database.sqlite --config=/home/foo/tppt/config.json

Change the command line parameters to point to the correct TPPT script directory.

TPPT Analysis software is used in dry run environment the same as in real TnT environment.
