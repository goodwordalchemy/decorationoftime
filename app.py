import os
from datetime import datetime
from flask import Flask, redirect, render_template, request, url_for
from flask_pymongo import PyMongo
from flask_sqlalchemy import SQLAlchemy
from gwa_spotify_api import SpotifyAuthAPI
from rauth import OAuth2Service

from config import config
from scrape_user_favorites import scrape_favorites


SCOPES = [
    'playlist-read-private',
    'user-top-read',
]

'''
The `ENVIRONMENT_NAME` needs to be set to 'production' or else it defaults
to 'development'
'''
config_name = os.environ.get('ENVIRONMENT_NAME') or 'development'

app = Flask(__name__)
app.config.from_object(config[config_name])

mongo = PyMongo(app)


spotify_api_config = {
    'SPOTIFY_CLIENT_ID': app.config['SPOTIFY_CLIENT_ID'],
    'SPOTIFY_CLIENT_SECRET': app.config['SPOTIFY_CLIENT_SECRET'],
    'SPOTIFY_CALLBACK_URL': app.config['SPOTIFY_CALLBACK_URL'],
}

@app.before_first_request
def load_spotify_api():
    global spotify_api
    spotify_api = SpotifyAuthAPI(
        assign_token=False, config=spotify_api_config, scopes_list=SCOPES
    )


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/authorize/spotify')
def spotify_authorize():
    authorize_url = spotify_api.get_authorize_url()

    return redirect(authorize_url)


@app.route('/callback/spotify')
def spotify_callback():
    auth_code = request.args['code']

    token = spotify_api.get_access_token(auth_code)
    spotify_api.assign_token(token=token)

    return redirect(url_for('spotify_scrape_data'))


@app.route('/scrape_data/spotify')
def spotify_scrape_data():
    user_profile_info = spotify_api.get('me')
    social_id = user_profile_info['id']
    display_name = user_profile_info['display_name']

    user = mongo.db.users.find_one({'user_id': social_id})

    if not user:
        user_favorites = scrape_favorites(spotify_api)
        user_favorites.update({
            'update_time': datetime.now(),
            'user_id': social_id,
        })
        result = mongo.db.users.insert_one(user_favorites)
        print('inserted one item with id: {}'.format(result.inserted_id))
    else:
        print('user already exists')

    return redirect(url_for('welcome'))


@app.route('/welcome')
def welcome():
    return render_template('welcome.html')
