import json
import random
import string
from functools import wraps

import httplib2
import os
import requests
from flask import make_response, jsonify, send_from_directory
from flask import request, render_template, redirect, url_for, flash
from flask import session as login_session
from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets
from werkzeug.utils import secure_filename

from catalog import app
from catalog.model.category import Category
from catalog.model.item import Item
from model.user import User
from db_setup import *

CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
IMAGE_FOLDER = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])


def generate_random_state():
    """Generate random state string in order to be used in every login"""
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                   for _ in xrange(32))


def render_template_with_session(template, **params):
    """This method will be called each time when rendering a new template.
        Other relevant information are also passed with it.
    """
    if params is not None:
        if 'categories' not in params:
            params['categories'] = session.query(Category).all()

        if 'selected_category' not in params:
            params['selected_category'] = session.query(Category).first()

        if 'STATE' not in params:
            params['STATE'] = generate_random_state()
            login_session['state'] = params['STATE']

        session_params = params
    else:
        session_params = dict()
    session_params['login_session'] = login_session
    return render_template(template, **session_params)


def redirect_to_first_available_category():
    """This will redirect to first category page"""
    return redirect('/'+str(session.query(Category).first().id))


def allowed_file(filename):
    """Checks whether uploaded files contains valid extensions"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(image_save_request):
    """This will save the file mentioned in the request in the
        UPLOAD_FOLDERspecified in the app config. Relevant
        warnings will be dispatched when the
        file name is not specified
    """
    if 'file' not in image_save_request.files:
        flash('No file part')
        return redirect(image_save_request.url)
    file = image_save_request.files['file']

    # Check emptiness of the file
    if file.filename == '':
        flash('No selected file')
        return redirect(image_save_request.url)
    # Check file is allowed
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.root_path,
                               app.config['UPLOAD_FOLDER'], filename))
    else:
        flash('Invalid File')
        return redirect(image_save_request.url)
    return filename


@app.route('/')
@app.route('/<int:cat_id>')
def index(cat_id=None):
    """This is the root of the application"""
    main_categories = session.query(Category)
    if main_categories.count() > 0:
        # If cat_id is not available redirect to 1st category available
        if cat_id:
            # Fetch the content according to the id
            sub_items = session.query(Item).filter_by(cat_id=cat_id)
            category = session.query(Category).filter_by(id=cat_id).first()

            if sub_items.count() == 0:
                sub_items = dict()
            return render_template_with_session("index.html",
                                                categories=main_categories
                                                .all(),
                                                items=sub_items,
                                                selected_category=category)
        else:
            return redirect_to_first_available_category()
    else:
        return render_template_with_session("index.html")


@app.route('/uploads/<path:image_name>')
def item_image_path(image_name):
    """This will return the path of the image which is inside
       the IMAGE_FOLDER"""
    return send_from_directory(IMAGE_FOLDER, image_name, as_attachment=True)


@app.route('/login')
def show_login():
    """This will render the login.html with the generated state string"""
    state = generate_random_state()
    login_session['state'] = state
    return render_template_with_session('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """This is the login point of the application"""

    # Checking whether response received from the form the client requested
    if request.args.get('state') != login_session['state']:
        return prepare_invalid_login_status('Login state for the current '
                                            'session is invalid')

    # Receiving the auth code sent by google servers
    code = request.data
    try:
        # Create credentials object via the flow object which
        # is generated by the client_secret.json.client_secret.
        # json is the file that is downloaded from the google
        # dev console. All information needs to be correct in
        # the server and client files including the redirect_url
        # in order for this try block to work
        credentials = get_credentials_object(code)
    except FlowExchangeError:
        return prepare_invalid_login_status('Failed to create '
                                            'credentials object')

    # Check that the access token is valid.
    access_token = credentials.access_token
    result = verify_access_token(access_token)

    # There is a problem in the access token
    if result.get('error') is not None:
        return prepare_invalid_login_status('Invalid Access Token. '
                                            'Error: ' +
                                            result.get('error'))

    # check  the token is for correct user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        return prepare_invalid_login_status("User ID in credentials "
                                            "object is not equivalent "
                                            "to google server User ID")

    # Making sure the correct application
    if result['issued_to'] != CLIENT_ID:
        return prepare_invalid_login_status("Invalid client Id")

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')

    # Checking whether  saved token is same as that is obtained
    # from credentials object
    if stored_access_token is not None \
            and stored_access_token == credentials.access_token \
            and gplus_id == stored_gplus_id:
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
    user = session.query(User).filter_by(id=login_session['user_id']).first()

    # if user not available create it
    if user is None:
        user = User(name=login_session['username'],
                    image=login_session['picture'],
                    id=login_session['user_id'],
                    email=login_session['email'])
        session.add(user)
        session.commit()

    return jsonify({
        'username': login_session['username'],
        'picture': login_session['picture'],
        'email': login_session['email']
    })


def prepare_invalid_login_status(message):
    """This will prepare Invalid login status message"""
    response = make_response(json.dumps(message), 401)
    response.headers['Content-Type'] = 'application/json'
    return response


def prepare_successful_status(message):
    """This will prepare Success login status message"""
    response = make_response(json.dumps(message), 200)
    response.headers['Content-Type'] = 'application/json'
    return response


def get_credentials_object(code):
    """This will generate credentials object from the client_secret.json"""
    oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
    oauth_flow.redirect_uri = "postmessage"
    credentials = oauth_flow.step2_exchange(code)
    return credentials


def verify_access_token(access_token):
    """Verify the access_token with google servers and return the result"""
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    return json.loads(h.request(url, 'GET')[1])


def revoke_access_token(access_token):
    """Revoke the access token that is already registered in google servers"""
    url = ("https://accounts.google.com/o/oauth2/revoke?"
           "token=%s" % access_token)
    h = httplib2.Http()
    response = h.request(url, 'GET')
    return response[0]


@app.route('/gdisconnect')
def gdisconnect():
    """This is the logout function of the application.
        This will clear the login session
        after revoking the access and return the relevant status message"""
    access_token = login_session.get('access_token')
    if access_token is None:
        return prepare_invalid_login_status('User credentials saved '
                                            'in session is empty')
    results = revoke_access_token(access_token)

    # Clear all login_session variables if revocation is successful
    # on google servers
    if results['status'] == '200':
        login_session.clear()

    else:
        return prepare_invalid_login_status('Revocation of access '
                                            'token on server failed.')

    return redirect_to_first_available_category()


def login_required(f):
    """This the annotation to check whether the user is
        authenticated in order to use specific functionality"""
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
            return render_template_with_session("add_item.html",
                                                category=category)
        else:
            name = request.form["name"]
            description = request.form["description"]
            image_name = save_image(request)
            new_item = Item(name=name, description=description,
                            cat_id=cat_id,
                            user_id=login_session['user_id'],
                            image_name=image_name)
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
                return render_template_with_session("edit_item.html",
                                                    category=item.category,
                                                    item=item)
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


@app.route('/delete_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def delete_item(item_id):
    """This route will delete an item"""
    if item_id:
        item = session.query(Item).filter_by(id=item_id).first()

        if item.user_id == login_session['user_id']:
            if request.method == 'GET':
                return render_template_with_session("delete_item.html",
                                                    item=item)
            else:
                # First remove the image then remove the database entry
                os.remove(os.path.join(app.root_path,
                                       app.config['UPLOAD_FOLDER'],
                                       item.image_name))
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
        return render_template_with_session("description.html",
                                            category=category,
                                            item=item)
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
        new_item = Category(name=name, user_id=login_session['user_id'])
        session.add(new_item)
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
                return render_template_with_session("edit_category.html",
                                                    category=category)
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
                return render_template_with_session("delete_category.html",
                                                    category=category)
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
