import json
import random
import string
from functools import wraps

import httplib2
import os
import requests
from flask import make_response, jsonify
from flask import request, render_template, redirect, url_for, flash
from flask import session as login_session
from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets
from werkzeug.utils import secure_filename

from catalog import app
from catalog.model.user import User
from db_setup import *

CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog"

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def render_template_with_session(template, **params):
    if params is not None:
        session_params = params
    else:
        session_params = dict()
    session_params['login_session'] = login_session
    return render_template(template, **session_params)


def redirect_to_first_available_category():
    return redirect('/'+str(session.query(Category).first().id))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(request):
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']

    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename))
    return filename

@app.route('/')
@app.route('/<int:cat_id>')
def index(cat_id=None):
    """This is the root of the application"""
    main_categories = session.query(Category)
    if main_categories.count() > 0:
        if cat_id:
            # Fetch the content according to the id
            sub_items = session.query(Item).filter_by(cat_id=cat_id)
            category = session.query(Category).filter_by(id=cat_id).first()

            if sub_items.count() == 0:
                sub_items = dict()
            return render_template_with_session("index.html", categories=main_categories, items=sub_items,
                                                selected_category=category)
        else:
            return redirect_to_first_available_category()
    else:
        return render_template_with_session("index.html")


@app.route('/login')
def show_login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template_with_session('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():

    # Checking whether response received from the form the client requested
    if request.args.get('state') != login_session['state']:
        return prepare_invalid_login_status('Login state for the current session is invalid')

    # Receiving the auth code sent by google servers
    code = request.data
    try:
        # Create credentials object via the flow object which is generated by the client_secret.json.
        # client_secret.json is the file that is downloaded from the google dev console
        # All information needs to be correct in the server and client files
        # including the redirect_url in order for this try block to work
        credentials = get_credentials_object(code)
    except FlowExchangeError:
        return prepare_invalid_login_status('Failed to create credentials object')

    # Check that the access token is valid.
    access_token = credentials.access_token
    result = verify_access_token(access_token)

    # There is a problem in the access token
    if result.get('error') is not None:
        return prepare_invalid_login_status('Invalid Access Token. Error: '+result.get('error'))

    # check  the token is for correct user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        return prepare_invalid_login_status("User ID in credentials object is not equivalent to google server User ID")

    # Making sure the correct application
    if result['issued_to'] != CLIENT_ID:
        return prepare_invalid_login_status("Invalid client Id")

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')

    # Checking whether  saved token is same as that is obtained from credentials object
    if stored_access_token is not None and stored_access_token == credentials.access_token and gplus_id == stored_gplus_id:
        return prepare_successful_status('User is already connected ')

    # Saving access_token and gplus_id
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['user_id'] = data['id']
    login_session['email'] = data['email']
    print 'users id',login_session['user_id']
    user = session.query(User).filter_by(id=login_session['user_id']).first()

    # if user not available create it
    if user is None:
        user = User(name=login_session['username'], image=login_session['picture'],
                    id=login_session['user_id'], email=login_session['email'])
        session.add(user)
        session.commit()

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


def prepare_invalid_login_status(message):
    response = make_response(json.dumps(message), 401)
    response.headers['Content-Type'] = 'application/json'
    return response


def prepare_successful_status(message):
    response = make_response(json.dumps(message), 200)
    response.headers['Content-Type'] = 'application/json'
    return response


def get_credentials_object(code):
    oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
    oauth_flow.redirect_uri = "postmessage"
    credentials = oauth_flow.step2_exchange(code)
    return credentials


def verify_access_token(access_token):
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    return json.loads(h.request(url, 'GET')[1])


def revoke_access_token(access_token):
    print access_token
    url = ("https://accounts.google.com/o/oauth2/revoke?token=%s" % access_token)
    h = httplib2.Http()
    response = h.request(url, 'GET')
    return response[0]


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    print access_token
    if access_token is None:
        return prepare_invalid_login_status('User credentials saved in session is empty')
    results = revoke_access_token(access_token)

# Clear all login_session variables if revocation is successful on google servers
    if results['status'] == '200':
        login_session.clear()

    else:
        return prepare_invalid_login_status('Revocation of access token on server failed.')

    return redirect_to_first_available_category()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            flash('You are not authorized')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


# Routing end points for items
@app.route('/add/item/<int:cat_id>', methods=['GET', 'POST'])
@login_required
def add_item(cat_id=None):
    """This will render add html form and save the filled form"""

    if cat_id:
        if request.method == "GET":
            category = session.query(Category).filter_by(id=cat_id).first()
            return render_template_with_session("add_item.html", category=category)
        else:
            name = request.form["name"]
            description = request.form["description"]
            image_name = save_image(request)
            new_item = Item(name=name, description=description, cat_id=cat_id, user_id=login_session['user_id'])
            session.add(new_item)
            session.commit()
            return redirect('/')
    else:
        return redirect('/')


@app.route('/edit/item/<int:cat_id>/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(cat_id, item_id):
    """This will edit an existing item. category id is not needed,
       but it is taken in order to keep consistency in the URL
    """
    if cat_id and item_id:
        item = session.query(Item).filter_by(id=item_id).first()
        if item.user_id == login_session['user_id']:

            if request.method == 'GET':
                return render_template_with_session("edit_item.html", category=item.category, item=item)
            else:
                name = request.form["name"]
                description = request.form["description"]
                item.name = name
                item.description = description
                session.add(item)
                session.commit()
                return redirect("/")
        else:
            flash('You are not authorized to edit this item')
            return redirect("/")

    else:
        return redirect("/")


@app.route('/delete_item/<int:item_id>',methods=['GET', 'POST'])
@login_required
def delete_item(item_id):
    """This route will delete an item"""

    if item_id:
        item = session.query(Item).filter_by(id=item_id).first()

        if item.user_id == login_session['user_id']:
            if request.method == 'GET':
                return render_template_with_session("delete_item.html", item=item)
            else:
                session.delete(item)
                session.commit()
        else:
            flash('You are not authorized to delete this item')
            return redirect("/")

    return redirect("/")


@app.route('/description/<int:item_id>')
def description_item(item_id):
    """This will render the descrition view"""
    item = session.query(Item).filter_by(id=item_id).first()
    if item is not None:
        category = item.category
        return render_template_with_session("description.html", category=category, item=item)
    else:
        redirect_to_first_available_category()


# Routing end points for categories
@app.route('/add/category/', methods=['GET', 'POST'])
@login_required
def add_category():
    """This will render add html form"""

    if request.method == 'GET':
        return render_template_with_session("add_category.html")
    else:
        name = request.form["name"]
        newItem = Category(name=name, user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        return redirect(url_for("index"))


@app.route('/edit/category/<int:cat_id>', methods=['GET', 'POST'])
@login_required
def edit_category(cat_id):
    """This will edit an existing category"""

    if cat_id:
        category = session.query(Category).filter_by(id=cat_id).first()
        if category.user_id == login_session['user_id']:
            if request.method == 'GET':
                return render_template_with_session("edit_category.html", category=category)
            else:
                name = request.form["name"]
                category.name = name
                session.add(category)
                session.commit()
                return redirect("/")
        else:
            flash('You are not authorized to edit this page')
            return redirect("/")
    else:
        return redirect("/")


@app.route('/delete_category/<int:cat_id>', methods=['GET', 'POST'])
@login_required
def delete_category(cat_id):
    """Deleting category"""

    if cat_id:
        category = session.query(Category).filter_by(id=cat_id).first()
        if category.user_id == login_session['user_id']:

            if request.method == 'GET':
                return render_template_with_session("delete_category.html", category=category)
            else:
                session.delete(category)
                session.commit()
        else:
            flash('You are not authorized to delete this page')
    return redirect("/")


# JSON end points

@app.route('/json/item/<int:item_id>')
@login_required
def item_json(item_id):
    """This will give json output for a given item"""
    item = session.query(Item).filter_by(id=item_id).first()
    if item is not None:
        return jsonify(item.serialize)
    else:
        return jsonify({})


@app.route('/json/category/<int:cat_id>')
@login_required
def category_json(cat_id):
    """This will give json output for a given category"""
    category = session.query(Category).filter_by(id=cat_id).first()
    if category is not None:
        return jsonify(category.serialize)
    else:
        return jsonify({})


@app.route('/json')
@login_required
def all_items_and_categories():
    """This will give json output for all the items in each category"""
    categories = session.query(Category)
    if categories.count() > 0:
        return jsonify([category.serialize for category in categories])
    else:
        return jsonify({})
