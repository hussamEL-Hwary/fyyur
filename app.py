#-----------------------------------#
# Imports
#-----------------------------------#
from datetime import datetime
import sys
import json
import dateutil.parser
import babel
from flask import (Flask, abort, 
                   render_template, 
                   request, Response, 
                   flash, redirect, url_for)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from config import *

#-----------------------------------#
# App Config.
# ----------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#------------------------------------#
# Models.
#------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String(100)))


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String)
    image_link = db.Column(db.String)
    
 
class Show(db.Model):
  __tablename__ = 'Show'

  id = db.Column(db.Integer, primary_key=True)
  start_time = db.Column(db.DateTime, nullable=False)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
  venue = db.relationship('Venue', backref=db.backref('venue_shows', lazy=True))
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
  artist = db.relationship('Artist', backref=db.backref('artist_show', lazy=True))

db.create_all()

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#---------------------------------------------------#
# Controllers.
#---------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  #num_upcoming_shows should be aggregated based on 
  # number of upcoming shows per venue.
  
  venues = Venue.query.all()
  # to group venues by state key -> state
  # value -> [city, [venues]]
  grouped_venues = {}
  result = []
  for venue in venues:
    if venue.state in grouped_venues.keys():
      grouped_venues[venue.state][1].append({
        "id": venue.id,
        "name": venue.name,
        "num_upcoming_shows": Show.query.
        filter(Show.venue_id==venue.id, Show.start_time > datetime.now()).count(),
      })
    else:
      grouped_venues[venue.state]=[]
      grouped_venues[venue.state].append(venue.city)
      grouped_venues[venue.state].append([])
      grouped_venues[venue.state][1].append({
        "id": venue.id,
        "name": venue.name,
        "num_upcoming_shows": Show.query.
        filter(Show.venue_id==venue.id, Show.start_time > datetime.now()).count(),
      })
    
  for k, v in grouped_venues.items():
    result.append({
        "city": v[0],
        "state": k,
        "venues": v[1]
        }
    )
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

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  past_shows = []
  upcoming_shows = []
  try:
    venue = Venue.query.get(venue_id)
    venue_shows = Show.query.filter_by(venue_id=venue_id)
    
    for show in venue_shows:
      if show.start_time > datetime.now():
        upcoming_shows.append({
        "artist_id": show.id,
        "artist_name": show.artist.name,
        "artist_image_link": show.artist.image_link,
        "start_time": str(show.start_time)
      })
      else:
        past_shows.append({
          "artist_id": show.id,
          "artist_name": show.artist.name,
          "artist_image_link": show.artist.image_link,
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
#  Create Venue
#  ----------------------------------------------------------------

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
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # get all artists
  artists = Artist.query.with_entities(Artist.id, Artist.name).all()
  return render_template('pages/artists.html', artists=artists)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  response={
    "count": 1,
    "data": [{
      "id": 4,
      "name": "Guns N Petals",
      "num_upcoming_shows": 0,
    }]
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # get specific artist based on id
  # check if id exist
  try:
    selected_artist = Artist.query.get(artist_id)
    # if artist exist
    # get shows related to artist
    shows = Show.query.filter_by(artist_id=artist_id).all()
    past_shows = []
    upcoming_shows = []
    for show in shows:
      if show.start_time >= datetime.now():
        upcoming_shows.append({
          "venue_id": show.venue_id,
          "venue_name": show.venue.name,
          "venue_image_link": show.venue.image_link,
          "start_time": str(show.start_time),
        })
      else:
        past_shows.append({
          "venue_id": show.venue_id,
          "venue_name": show.venue.name,
          "venue_image_link": show.venue.image_link,
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

#  Update
#  ----------------------------------------------------------------
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


#  Create Artist
#  ----------------------------------------------------------------

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
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  shows = Show.query.all()
  data = []
  for val in shows:
    temp = {
      "venue_id": val.id,
      "venue_name": val.venue.name,
      "artist_id": val.artist_id,
      "artist_name": val.artist.name,
      "artist_image_link": val.artist.image_link,
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



  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead

  # on successful db insert, flash success
  flash('Show was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
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

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
