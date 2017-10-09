# This file is the main file that needs to be run with the command python. This will run the
# main file as well as start the server for the given configuration

from catalog import app
from catalog import main

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.debug = True
    app.run(host='0.0.0.0', port=8085)
