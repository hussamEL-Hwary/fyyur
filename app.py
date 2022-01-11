# Imports

import sys
import json
import logging
from logging import Formatter, FileHandler
from datetime import datetime

from flask import (Flask, abort, 
                   render_template, 
                   request, Response, 
                   flash, redirect, url_for)
from flask_moment import Moment
from flask_wtf import Form
from flask_migrate import Migrate

from models import db, Venue, Artist, Show
from forms import ShowForm, VenueForm, ArtistForm 
from utils import format_datetime
from config import SQLALCHEMY_DATABASE_URI, SECRET_KEY, WTF_CSRF_SECRET_KEY

# App Config.
app = Flask(__name__)
moment = Moment(app)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = SECRET_KEY
app.config["WTF_CSRF_SECRET_KEY"] = WTF_CSRF_SECRET_KEY
db.app = app
migrate = Migrate(app, db)
db.init_app(app)
app.jinja_env.filters['datetime'] = format_datetime


# Endpoints.

@app.route('/')
def index():
  return render_template('pages/home.html')

#  Venues
@app.route('/venues')
def venues():
  #num_upcoming_shows should be aggregated based on 
  # number of upcoming shows per venue.
  
  venues = Venue.query.all()
  result = []
  # get distnict city and states
  distinct_venues = Venue.query.distinct(Venue.state, Venue.city)
  for venue in distinct_venues:
    pre_venues = []
    for item in Venue.query.filter(Venue.state==venue.state, Venue.city==venue.city):
      pre_venues.append({
        "id": item.id,
        "name": item.name,
        "num_upcoming_shows": Show.query.
        filter(Show.venue_id==item.id, Show.start_time > datetime.now()).count(),
      })
    result.append({
        "city": venue.city,
        "state": venue.state,
        "venues": pre_venues
        })

  return render_template('pages/venues.html', areas=result)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # get search term
  search_term = request.form.get('search_term', '')
  # filter by search_term
  result = Venue.query.filter(Venue.name.ilike('%'+search_term+'%')).all()
  response={
    "count": len(result),
    "data": []
  }
  for venue in result:
    response['data'].append({
      "id": venue.id,
      "name": venue.name,
      "num_upcoming_shows": Show.query.
      filter(Show.venue_id==venue.id, Show.start_time > datetime.now()).count(),
    })

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  past_shows = []
  upcoming_shows = []
  try:
    venue = Venue.query.get(venue_id)
    venue_shows = Show.query.join(Venue).filter(Show.venue_id==venue_id)
    
    for show in venue_shows:
      if show.start_time > datetime.now():
        upcoming_shows.append({
        "artist_id": show.id,
        "artist_name": show.artist_show.name,
        "artist_image_link": show.artist_show.image_link,
        "start_time": str(show.start_time)
      })
      else:
        past_shows.append({
          "artist_id": show.id,
          "artist_name": show.artist_show.name,
          "artist_image_link": show.artist_show.image_link,
          "start_time": str(show.start_time)
        })
    result = {
      "id": venue.id,
      "name": venue.name,
      "genres": venue.genres,
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "website": venue.website,
      "facebook_link": venue.facebook_link,
      "seeking_talent": venue.seeking_talent,
      "seeking_description": venue.seeking_description,
      "image_link": venue.image_link,
      "past_shows": past_shows,
      "upcoming_shows": upcoming_shows,
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_venue.html', venue=result)
  except:
    abort(404)

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  venue_form = VenueForm(request.form)
  # validate inputs
  if venue_form.validate():
    error = False
    try:
      # create new venue
      new_venue = Venue(name=venue_form.name.data,
                        city=venue_form.city.data,
                        state=venue_form.state.data,
                        address=venue_form.address.data,
                        phone=venue_form.phone.data,
                        image_link=venue_form.image_link.data,
                        facebook_link=venue_form.facebook_link.data,
                        website=venue_form.website_link.data,
                        seeking_talent=venue_form.seeking_talent.data,
                        seeking_description=venue_form.seeking_description.data,
                        genres=venue_form.genres.data
                        )
      db.session.add(new_venue)
      db.session.commit()
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
      return render_template('pages/home.html')
    except:
      error = True
      flash("An error occurred.!")
      db.session.rollback()
    finally:
      db.session.close()
    if error:
      return render_template('forms/new_venue.html', form=venue_form)
  else:
    flash(venue_form.errors)
    return render_template('forms/new_venue.html', form=venue_form)

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # SQLAlchemy ORM to delete a record. 
  # Handle cases where the session commit could fail.
  try:    
    current_venue = Venue.query.get(venue_id)
    db.session.delete(current_venue)
    db.session.commit()
    # delete related shows
    #related_shows = Show.query.filter(Show.venue_id=venue_id).delete()
  except:
    db.session.rollback()
    abort(500)
  finally:
    db.session.close()

  return redirect(url_for('index'))

#  Artists
@app.route('/artists')
def artists():
  # get all artists
  artists = Artist.query.with_entities(Artist.id, Artist.name).all()
  return render_template('pages/artists.html', artists=artists)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # get search term
  search_term = request.form.get('search_term','')
  # filter by search term
  result = Artist.query.filter(Artist.name.ilike('%'+search_term+'%')).all()
  response={
    "count": len(result),
    "data": []
  }

  for artist in result:
    response["data"].append({
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": Show.query.
      filter(Show.artist_id==artist.id, Show.start_time > datetime.now()).count()
    })
  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # get specific artist based on id
  # check if id exist
  try:
    selected_artist = Artist.query.get(artist_id)
    # if artist exist
    # get shows related to artist
    shows = Show.query.join(Artist).filter(Artist.id==artist_id).all()
    past_shows = []
    upcoming_shows = []
    for show in shows:
      if show.start_time >= datetime.now():
        upcoming_shows.append({
          "venue_id": show.venue_id,
          "venue_name": show.venue_shows.name,
          "venue_image_link": show.venue_shows.image_link,
          "start_time": str(show.start_time),
        })
      else:
        past_shows.append({
          "venue_id": show.venue_id,
          "venue_name": show.venue_shows.name,
          "venue_image_link": show.venue_shows.image_link,
          "start_time": str(show.start_time),
        })
    result = {
      "id": selected_artist.id,
      "name": selected_artist.name,
      "genres": selected_artist.genres,
      "city": selected_artist.city,
      "state": selected_artist.state,
      "phone": selected_artist.phone,
      "website": selected_artist.website,
      "facebook_link": selected_artist.facebook_link,
      "seeking_venue": selected_artist.seeking_venue,
      "seeking_description": selected_artist.seeking_description,
      "image_link": selected_artist.image_link,
      "past_shows": past_shows,
      "upcoming_shows": upcoming_shows,
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows),
    }
    return render_template('pages/show_artist.html', artist=result)
  except:
    abort(404)


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  try:
    artist = Artist.query.get(artist_id)
    # if artist exist init form data with artist
    form = ArtistForm(name=artist.name,
                      city=artist.city, 
                      state=artist.state,
                      phone=artist.phone,
                      image_link=artist.image_link,
                      genres=artist.genres,
                      facebook_link=artist.facebook_link,
                      website_link=artist.website,
                      seeking_venue=artist.seeking_venue,
                      seeking_description=artist.seeking_description)
    # TODO: populate form with fields from artist with ID <artist_id>
    return render_template('forms/edit_artist.html', form=form, artist=artist)
  except:
    abort(404)


  
@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  try:
    artist = Artist.query.get(artist_id)
    form = ArtistForm(request.form)
    if form.validate():
      artist.name = form.name.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.phone = form.phone.data
      artist.genres = form.genres.data
      artist.image_link = form.image_link.data
      artist.facebook_link = form.facebook_link.data
      artist.website = form.website_link.data
      artist.seeking_venue = form.seeking_venue.data
      artist.seeking_description = form.seeking_description.data

      db.session.add(artist)
      db.session.commit()
      flash("Artist updated successfully!")
      return redirect(url_for('show_artist', artist_id=artist_id))
    else:
      flash("Please check all data is correct!")
      return render_template('forms/edit_artist.html', form=form, artist=artist)
  except:
    abort(404)
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  try:
    # get venue by id
    venue = Venue.query.get(venue_id)
    # initailize form with data
    form = VenueForm(name=venue.name,
                    city=venue.city, 
                    state=venue.state,
                    phone=venue.phone,
                    address=venue.address,
                    image_link=venue.image_link,
                    genres=venue.genres,
                    facebook_link=venue.facebook_link,
                    website_link=venue.website,
                    seeking_talent=venue.seeking_talent,
                    seeking_description=venue.seeking_description)
    return render_template('forms/edit_venue.html', form=form, venue=venue)
  except:
    abort(404)
  

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  try:
    # venue record with ID <venue_id> using the new attributes
    venue = Venue.query.get(venue_id)
    form = VenueForm(request.form)
    if form.validate():
      venue.name = form.name.data
      venue.city = form.city.data
      venue.state = form.state.data
      venue.phone = form.phone.data
      venue.address = form.address.data
      venue.image_link = form.image_link.data
      venue.genres = form.genres.data
      venue.facebook_link = form.facebook_link.data
      venue.website = form.website_link.data
      venue.seeking_talent = form.seeking_talent.data
      venue.seeking_description = form.seeking_description.data
      
      db.session.add(venue)
      db.session.commit()
      flash("Venue updated successfully")
      return redirect(url_for('show_venue', venue_id=venue_id))
    else:
      flash("Data is not valid")
      return redirect(url_for('show_venue', venue_id=venue_id))
  except:
    abort(404)

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # get form data
  form = ArtistForm(request.form)
  # validate input data
  if form.validate():
    error =False
    
    try:
      new_artist = Artist(name=form.name.data,
                          city=form.city.data,
                          state=form.state.data,
                          phone=form.phone.data,
                          image_link=form.image_link.data,
                          facebook_link=form.facebook_link.data,
                          website=form.website_link.data,
                          seeking_venue=form.seeking_venue.data,
                          seeking_description=form.seeking_description.data,
                          genres=form.genres.data)
      db.session.add(new_artist)
      db.session.commit()
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
      return render_template('pages/home.html')
    except:
      error = True
      flash("An error occurred.!")
      print(sys.exc_info())
      db.session.rollback()
    finally:
      db.session.close()
    if error:
      return render_template('forms/new_artist.html', form=form)
  else:
    flash("Please check input data")
    return render_template('forms/new_artist.html', form=form)

#  Shows

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  shows = Show.query.join(Venue).all()
  data = []
  for val in shows:
    temp = {
      "venue_id": val.id,
      "venue_name": val.venue_shows.name,
      "artist_id": val.artist_id,
      "artist_name": val.artist_show.name,
      "artist_image_link": val.artist_show.image_link,
      "start_time": str(val.start_time)
    }
    data.append(temp)
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  form = ShowForm(request.form)
  if form.validate():
    # check if venue_id exists in db
    if form.venue_id.data:
      try:
        temp_venue_id = int(form.venue_id.data)
        print(temp_venue_id)
        venue = Venue.query.get(temp_venue_id)
      except:
        flash("Venue id doesn't exist")
        return render_template('forms/new_show.html', form=form)
    # check if artist_id exists in db
    if form.artist_id.data:
      try:
        temp_artisit_id = int(form.artist_id.data)
        artist = Artist.query.get(temp_artisit_id)
      except:
        flash("Artist id doesn't exist")
        return render_template('forms/new_show.html', form=form)
    try:
      new_show = Show(start_time=form.start_time.data, 
                      venue_id=form.venue_id.data,
                      artist_id=form.artist_id.data)
      db.session.add(new_show)
      db.session.commit()
      flash("New show successfully added!")
      return render_template('pages/home.html')
    except:
      flash("An error occurred")
      return render_template('forms/new_show.html', form=form) 
  else:
    flash("form isn't vaild")
    return render_template('forms/new_show.html', form=form)

  # on successful db insert, flash success
  flash('Show was successfully listed!')
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# starting app...

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
