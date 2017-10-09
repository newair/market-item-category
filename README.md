Online Market Item Catalog  Amila Ishara (Udacity)

This application is hosted in heroku. Use this [URL](https://item-catalog-1.herokuapp.com) to access.

## Introduction
This project contains source code for item caltalog project which implements CRUD operations of item categories and sub categories authenticated by 3rd party authentication systems.

## Prerequisites
* Python 2.7 with requirements.txt file or checkout fullstack nanodegree back end project.
* If db access is desired you may install sqlite3 seperately
* Browser Javascript enabled.

## Supported Browsers
* Chrome
* FireFox
* IE>11
* Safari

## How to Run

* Install Oracle Virtual Box
* Install Vagrant and put vagrant up in the project
* put vagrant ssh and navigate to project root which is in vagrant directory
* Run the command python app.py
* To create your own client_secret.json follow the Create client.json
* Existing database is named itemcatalog.db. If you want to set up new db follow the Setup DB

## Create client.json

* Go to [Google cloud platform console](https://console.cloud.google.com/home/dashboard)
* Create a new application and go to its dashboard
* Go to API's and Services and then Create Crendentials -> OAuth Client ID
* Create a web application project and give suitable name
* Enter the domains you want your app to run including localhost
    eg: http://localhost:8085, https://item-catalog-1.herokuapp.com
* Put authorized redirect url's
    eg: http://localhost:8085, https://item-catalog-1.herokuapp.com
* Save the form and download the client_secret.json
* Replace the value of data-clientid in layout.html with Client ID in console or client_secret.json

## Setup DB

* Create your own db with SQLite3 and replace itemcatalog.db
* link your db file inside the create_engine method in db_setup.py

## Access JSON end points

* /json to access all information
* /json/category/<int:cat_id> to access category specific information
* /json/item/<int:item_id> to access item specific information

## References

* Udacity Lessons
* Random images from google search just for the demo purposes
* Google developer console and Oauth docs
* Assistance from Stack overflow already posted questions
* Jinja 2 And Flask references
* Bootstrap docs
* Sqlite3 docs
* SQLAlchemy docs
* Heroku docs in order to deploy