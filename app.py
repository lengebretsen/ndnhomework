from flask import Flask, jsonify, make_response, request, render_template, abort, redirect, url_for
from math import radians, cos, sin, asin, sqrt
import uuid
from pymongo import MongoClient
from operator import itemgetter

def connect():
    """
    Initiate connection to mongodb
    """
    connection = MongoClient('localhost',27017)
    handle = connection['ndnhomework']
    #handle.authenticate("demo-user","12345678")
    return handle
    
app = Flask(__name__)
db = connect()


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad Request' } ), 400)

@app.route('/')
def index_page():
    return redirect(url_for('get_videos'))
    
@app.route('/videos', methods=['GET'] )
def get_videos():
    """
    Returns a list of all videos in the database.
    """
    # This works ok for small datasets, but since it's reading the whole videos collection into memory
    # the wheels come off once the dataset starts getting large. Seems like the best way to handle this 
    # is to paginate our returns so that we only pull the videos back a few at a time.
    return jsonify( {'Videos' : retrieve_all_videos() })
    
@app.route('/videos/<video_id>', methods = ['GET'])
def get_video(video_id):
    """
    Retrieves a single video by Id.
    Returns 404 if video can't be found
    """
    video = retrieve_one_video(video_id)
    if video == None:
        abort(404)
    return jsonify(video)
    
@app.route('/videos', methods = ['POST'])
def create_video():
    """
    Insert a new video and return the newly created video with Id.
    Returns 400 if required fields are missing.
    """
    if not is_valid_video(request.json, True):
        abort(400)
            
    new_id = str(uuid.uuid1()) # generate a new UUID to use for the video id
    video = {
        'Video':{
            'Id': new_id,
            'Name': request.json['Video']['Name'],
            'Location':{
                'Lat':request.json['Video']['Location']['Lat'],
                'Long':request.json['Video']['Location']['Long']
            }
        }
    }
    db.videos.insert(video)
    return jsonify( {'Video' : video['Video']} ), 201 # Display the newly inserted document to the user


@app.route('/videos/<video_id>', methods = ['PUT'])
def put_video(video_id):
    """
    Update a video by Id. Replaces the entire document!
    Returns 400 if required fields are missing.
    """
    if not is_valid_video(request.json, True):
        abort(400)
    
    request.json['Video']["Id"] = video_id
    update_status = db.videos.update({'Video.Id':video_id}, {'$set': request.json}, upsert=False)
    if update_status["updatedExisting"]:
        return jsonify( request.json )
    else:
        abort(404) # document not found
    

@app.route('/videos/<video_id>', methods = ['PATCH'])
def patch_video(video_id):
    """
    Update a video by Id. Allows for partial update of a video.
    
    Returns a 400 if value of an field to update is not valid.
    """
    if not request.json:
        abort(400) # malformed request
    if 'Name' in request.json['Video'] and type(request.json['Video']['Name']) is not unicode:
        abort(400) #type mismatch
    if 'Location' in request.json['Video']:
        if 'Lat' in request.json['Video']['Location'] and not is_number(request.json['Video']['Location']['Lat']):
            abort(400) #type mismatch
        if 'Long' in request.json['Video']['Location'] and not is_number(request.json['Video']['Location']['Long']):
            abort(400) #type mismatch
    #update values
    updated = retrieve_one_video(video_id)
    if updated == None:
        abort(404)
    
    #Ensure any missing values are replaced with the original values so we don't erase anything
    updated['Video']['Name'] = request.json['Video'].get('Name', updated['Video']['Name'])
    if 'Location' in request.json['Video']:
        updated['Video']['Location']['Lat'] = request.json['Video']['Location'].get('Lat', updated['Video']['Location']['Lat'])
        updated['Video']['Location']['Long'] = request.json['Video']['Location'].get('Long', updated['Video']['Location']['Long'])
    
    update_status = db.videos.update({'Video.Id':video_id}, {'$set': updated}, upsert=False)
    return jsonify( updated )

@app.route('/videos/<video_id>', methods = ['DELETE'])
def delete_video(video_id):
    result = db.videos.remove({'Video.Id':video_id})
    app.logger.debug(result)
    if result['n'] == 0:
        abort(404)
    return jsonify( { 'success': 'Deleted id: %s' % video_id } )    
    

@app.route('/playlists', methods = ['GET'])
def retrieve_playlist():
    """
    Retrieves an ordered playlist of videos within the specified radius of an origin point.
    Playlist is ordered by ascending distance from origin.
    """
    playlist = []
    
    #check for required query params
    if not request.args.get('lat') or not request.args.get('long') or not request.args.get('radius') or \
       not is_number(request.args.get('lat')) or not is_number(request.args.get('long')) or not is_number(request.args.get('radius')):
        abort(400)
        
    originLat = float(request.args.get('lat'))
    originLon = float(request.args.get('long'))
    radius = float(request.args.get('radius'))
         
    # Looping through all the videos in the DB to calculate the difference between origin and video location
    # this is obviously terribly inefficient since we have to hit every entry. Better approach would be to divide the
    # videos up by location somehow so that we're looking at a relatively small bucket of videos with a similar 
    # geographic location to do our distance comparison on. 
    #
    # Something along the lines of geohash based proximity search as described in the links below:
    #
    # https://github.com/yinqiwen/ardb/blob/master/doc/spatial-index.md
    # https://github.com/davetroy/geohash-js
    videos = retrieve_all_videos()
    for video in videos:
        destLat = video['Video']['Location']['Lat']
        destLon = video['Video']['Location']['Long']
         
        distance = haversine(originLat, originLon, destLat, destLon)
        if distance <= radius:
            video["distance"] = distance # temporarily modify our videos so we have something to sort them on
            playlist.append(video) # distance is within the radius so add it to the result list
    
    sorted_list = sorted(playlist, key=itemgetter('distance')) # sort the list by distance
    for element in sorted_list:
        app.logger.debug(element)
        del element['distance'] # strip the distance elements back out of our dict
        
    return jsonify( { 'Playlist' : sorted_list } ) 
     

def is_valid_video(json, ignore_id):
    """
    Validates JSON document for videos 
    """
    if not json or not 'Name' in json['Video'] or not 'Location' in json['Video'] or \
       not 'Lat' in json['Video']['Location'] or not 'Long' in json['Video']['Location']:
        return False # Missing required fields

    if not ignore_id:
        return 'Id' in json['Video'] and type(json['Video']['Id']) is unicode
        
    if type(json['Video']['Name']) is not unicode or not is_number(json['Video']['Location']['Lat']) or \
       not is_number(json['Video']['Location']['Long']):
        return False #type mismatch
        
    return True # JSON validates

def retrieve_all_videos():
    """
    Return a list of all documents in the mongodb videos collection
    """
    videos = list(db.videos.find({}, {'_id':False})) #Filter out the ObjectIds since we don't need to display them
    return videos

def retrieve_one_video(video_id):
    """
    Return one video retrieved from mongodb by id
    """
    video = db.videos.find_one({'Video.Id':video_id}, {'_id':False})
    return video     

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) using haversine formula
    """
    # convert decimal degrees to radians 
    dlon = radians(lon2 - lon1) 
    dlat = radians(lat2 - lat1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    
    # haversine formula 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 

    # Radius of the earth
    #r = 6371 #kilometers
    r = 3958.76 #miles
    return r * c

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

if __name__ == '__main__':
    app.debug = True
    app.run()