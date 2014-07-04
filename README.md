NDN Homework Assignment
====================

Prerequisites
----------------
* mongodb
* python environment running:
 * flask
 * pymongo
 

Running the Application
----------------
* Ensure mongodb is running and has a database called ndnhomework
* Create a new collection called videos
* Load the data from videos.json into the videos collection
* Start the flask application
 * python app.py
 

Available REST Endpoints
------------------
* GET /videos
 * Returns a list of all videos in the database 
* GET /videos/&lt;Id&gt;
 * Returns the video with the specified Id
* POST /videos
 * Create a new video
* PUT /videos/&lt;Id&gt;
 * Update (replace) video with specified Id
* PATCH /videos/&lt;Id&gt;
 * Partial update of video with specified Id 
* DELETE /videos/&lt;Id&gt;
 * Deleted the video with specified Id 
* GET /playlists?lat=&lt;lattitude&gt;&long=&lt;longitude&gt;&radius=&lt;radius&gt;
 * Returns a list of videos geotagged to a location within a radius of the origin point 


Postman HTTP/REST Client
------------------
I used Postman for testing my application and exported my saved requests to demonstrate functionality. It's a browser plugin for chrome that makes testing against RESTful APIs very straightforward.

My exported requests are available here: https://www.getpostman.com/collections/da1d1ba58d51397c2361
or in a JSON file bundled with my application.

If you need to download a copy of Postman you can get it here: http://www.getpostman.com/
