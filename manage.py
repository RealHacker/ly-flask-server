from flask import Flask, render_template,g,request,make_response,jsonify
import MySQLdb;
import shutil;
import os;
import urllib2;
import random;
from PIL import Image;
from datetime import datetime,date,timedelta;

app = Flask(__name__)

def connectDB():
	g.conn = MySQLdb.connect(db="TONGQUETAI", user="root", passwd="123456", charset="utf8");
	g.cursor = g.conn.cursor();

@app.before_request
def before_request():
	connectDB();

@app.teardown_request
def teardown_request(exception):
	g.conn.close();

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/starlist')
def starlist():
	query = "select * from Star order by id";
	g.cursor.execute(query);
	records = g.cursor.fetchall(); 
	
	stars = [];
	iconPrefix = "http://tongque.net.cn/thumbnail/stars/icon/"
	for record in records:
		starID = record[0];
		icon = iconPrefix+record[1]+".jpg";
		name = record[2];
		city = record[4];
		stars.append({
			"ID": starID,
			"icon": icon,
			"name": name,
			"city": city
		});
	
	return jsonify(stars=stars);

@app.route('/startoday')
def startoday():
	q="select starID from Seq";
	g.cursor.execute(q);
	starID = g.cursor.fetchone()[0];

	return starinfo(starID);

@app.route('/star/<starid>')
def starinfo(starid):
	iconPrefix = "http://tongque.net.cn/thumbnail/stars/icon/"
	thumbPrefix = "http://tongque.net.cn/thumbnail/stars/thumbnail"	

	query = "select * from Star where id=%s"%starid;
	g.cursor.execute(query);
	record = g.cursor.fetchone();
	
	icon = iconPrefix+record[1]+".jpg";
	weiboID = record[1];
        name = record[2];
	description = record[3];
        city = record[4];
	xingzuo = record[5];
	votes = int(record[6]);

	albums = [];
	query = "select id, count from staralbum where starID=%s"%starid;
	g.cursor.execute(query);
	records = g.cursor.fetchall();
	for r in records:
		thumbnails = [];
		images = [];
		widths = [];
		heights = [];
		albumID = r[0];
		count = r[1];
		q = "select link, path, width, height from starphoto where albumID=%s"%albumID;
		g.cursor.execute(q);
		photos = g.cursor.fetchall();
		for p in photos:
			images.append(p[0]);
			thumbnails.append(thumbPrefix+p[1]);
			widths.append(p[2]);
			heights.append(p[3]);
		album = {
			"count": count,
			"thumbnails": thumbnails,
			"images": images,
			"widths": widths,
			"heights": heights
		};
		albums.append(album);
	star = {
		"ID": starid,
		"weiboID": weiboID,
		"icon": icon,
		"name": name,
		"description": description,
		"city": city,
		"xingzuo": xingzuo,
		"votes": votes,
		"albums": albums
	};
	return jsonify(star=star);

@app.route('/vote/<starid>')
def vote(starid):
	query = "update Star set vote=vote+1 where id=%s"%starid;
	g.cursor.execute(query);
	g.conn.commit();
	
	return jsonify(result="OK");

@app.route('/stats', methods=['GET'])
def getStats():
	retString = "";
	q1="select count(*) from Device";
	g.cursor.execute(q1);
	record = g.cursor.fetchone();
	retString=retString+"Total User Count:\t%d"%record[0]+"<br>";

	dateStr = date.today().isoformat();
	sevenDaysAgo = date.today()+timedelta(days=-7);
	dateStr2= sevenDaysAgo.isoformat();
	q2 = "select count(distinct deviceID) from Action where date(time)='%s'"%dateStr;
	g.cursor.execute(q2);
	record = g.cursor.fetchone();
        retString=retString+"Active User Count Today:\t%d"%record[0]+"<br>";
	q21="select count(distinct deviceID) from Action where date(time)>='%s'"%dateStr2;
	g.cursor.execute(q21);
	record = g.cursor.fetchone();
	retString = retString+"Active User Count in last 7 days:\t%d"%record[0]+"<br>";

	q3 = "select count(*) from Membership;"
	g.cursor.execute(q3);
        record = g.cursor.fetchone();
        retString=retString+"Total Members Count:\t%d"%record[0]+"<br>";
	
	q4 = "select count(*) from Membership where date(expireDate)='%s'"%dateStr;
	g.cursor.execute(q4);
        record = g.cursor.fetchone();
        retString=retString+"Members Joined Today:\t%d"%record[0]+"<br>";

	q5 = "select count(*) from Message where isRead=1";
        g.cursor.execute(q5);
        record = g.cursor.fetchone();
        retString=retString+"Total Messages Read:\t%d"%record[0]+"<br>";

	q6 = "select count(*) from Action where action='save' and date(time)='%s'"%dateStr;
        g.cursor.execute(q6);
        record = g.cursor.fetchone();
        retString=retString+"Download operations today:\t%d"%record[0]+"<br>";

 	q7 = "select count(*) from Action where action='fav' and date(time)='%s'"%dateStr;
        g.cursor.execute(q7);
        record = g.cursor.fetchone();
        retString=retString+"Favorite operations today:\t%d"%record[0]+"<br>";

	q8 = "select count(*) from Action where action='share' and date(time)='%s'"%dateStr;
        g.cursor.execute(q8);
        record = g.cursor.fetchone();
        retString=retString+"Share operations today:\t%d"%record[0]+"<br>";

	q9 = "select count(*) from (select count(action) as result, deviceID from Action where action='login' group by deviceID order by result) as temp where result>=3;";
	g.cursor.execute(q9);
        record = g.cursor.fetchone();
        retString=retString+"Users who have logged in >=3 times:\t%d"%record[0]+"<br>";

	retString = retString+"<br>";
	for i in range(0,23):
		q10 = "select count(*) from Action where date(time)='%s' and hour(time)=%d"%(dateStr,i);
		g.cursor.execute(q10);
		record = g.cursor.fetchone();
		retString = retString+"Actions taken today in hour %d: %d"%(i, record[0])+"<br>";

	return retString;

@app.route('/apply', methods=['GET'])
def getApply():
	applicants = [];
	q10="select parameter from Action where action='apply'";
	g.cursor.execute(q10);
	records = g.cursor.fetchall();
	for record in records:
		string = str(record[0]);
		unicodestr = string.decode("utf-8");
		applicants.append(unicodestr);
	return jsonify(app=applicants);
	
@app.route('/setreview',methods=['POST'])
def setreview():
	print "IN SET REVIEW"
#	assert request.method=='POST'
	dic =request.form;
	
	albumID = dic['album'];
	if dic['deleted']=='':
		deleted=[];
	else:
		deleted = dic['deleted'].split(',');
	ordered = dic['order'].split(',');
	level = int(dic['level']);
	cut = int(dic['cut']);
	
	for delID in deleted:
		#Get the file path by ID
		pathStmt = "select filePath, thumbnailPath from Photo where id=%s"%delID;
		g.cursor.execute(pathStmt);
		record = g.cursor.fetchone();
		filePath = record[0];
		thumbnailPath = record[1];
	
		#delete the thumbnail and file
		if os.path.isfile(filePath):
			os.remove(filePath);
		if os.path.isfile(thumbnailPath):
			os.remove(thumbnailPath);
		print "deleting files";

		#Delete the photo from Photo/PhotoAlbum/PhotoInfo/PhotoURL tables
		delStmt1 = "delete from PhotoInfo where photoID=%s"%delID;
		delStmt2 = "delete from PhotoURL where photoID=%s"%delID;
		delStmt3 = "delete from PhotoAlbum where photoID=%s"%delID;
		delStmt4 = "delete from Photo where id=%s"%delID;

		g.cursor.execute(delStmt1);
		g.cursor.execute(delStmt2);
		g.cursor.execute(delStmt3);
		g.cursor.execute(delStmt4);
		g.conn.commit();
		print "deleting records"
	#Change the idx value of other photos
	imgCount = len(ordered);
	for i in range(0, imgCount):
		updateStmt = "update PhotoAlbum set idx=%d where photoID=%s"%(i, ordered[i]);
		g.cursor.execute(updateStmt);
		g.conn.commit();
	print "Saving index values"

	#Update the album imageCount
	updateStmt = "update Album set imageCount=%d where id=%s"%(imgCount, albumID);
	g.cursor.execute(updateStmt);
	g.conn.commit();
	print "Updating image count"

	#check if the album has been reviewed or not
	chkStmt = "select count(*) from AlbumReview where albumID=%s"%albumID;
	g.cursor.execute(chkStmt);
	cnt = g.cursor.fetchone()[0];
	#if the review doesn't exist, insert one
	if cnt == 0:
		insertStmt = "insert into AlbumReview (albumID, reviewed, level, cut) values (%s, %s, %d, %d)"%(albumID, 'TRUE',level, cut);
		g.cursor.execute(insertStmt);
		g.conn.commit();
	#else update the review's level and cut
	else:
		updateStmt = "update AlbumReview set level=%d,cut=%d where albumID=%s"%(level, cut, albumID);
		g.cursor.execute(updateStmt);
		g.conn.commit();
	print "updating review record"	
	
	return make_response("OK");

@app.route('/review/<int:albumID>')
def reviewAlbum(albumID):
	return doReview(albumID);
	
@app.route('/review')
def review():
	return doReview('');
	
def doReview(arg):
	if arg=='':
	# select a random album that has not been reviewed
		query = "select * from Album where id not in (select albumID from AlbumReview where reviewed=TRUE) and identifier not like '%m1905%' order by RAND() LIMIT 1";
	else:
		query = "select * from Album where id=%s"%arg;
	g.cursor.execute(query);
	result = g.cursor.fetchone();		

	album = {
		"albumID": result[0],
		"identifier": result[1],
		"albumURL": result[2],
		"imageCount": result[3]
	};

	# get information of the album's photos
	photo_query = "select PhotoAlbum.idx, Photo.id, Photo.filePath, Photo.thumbnailPath, PhotoURL.URL from Photo,PhotoAlbum, PhotoURL where PhotoAlbum.albumID=%d and PhotoAlbum.photoID = Photo.id and PhotoURL.photoID = Photo.id ORDER BY PhotoAlbum.idx"%album["albumID"];
	g.cursor.execute(photo_query);
	results = g.cursor.fetchall();

	photos=[];
	for record in results:
		thumbimg = "http://www.tongque.net.cn/thumbnail"+record[3][14:];
		photos.append({
			"idx": record[0],
			"ID": record[1],
			"filePath": record[2],
			"thumbnail": thumbimg,
			"URL": record[4]
		});
		
	return render_template('review.html', album=album, photos = photos);	

@app.route('/videoreview')
def videoreview():
	query = "select id,identifier, videoURL from video where id not in (select videoID from VideoReview where reviewed=TRUE) order by rand() limit 5";
	g.cursor.execute(query);
	records = g.cursor.fetchall();
	
	ids = [];
	thumbs = [];
	videos = [];

	for record in records:
		ids.append(record[0]);
		thumb = "http://tongque.net.cn/video/%s.jpg"%record[1];
		thumbs.append(thumb);
		videos.append(record[2]);
	
	return render_template('videoreview.html', ids=ids, thumbs = thumbs, videos=videos);

@app.route('/setvideo', methods = ['POST'])
def setvideoreview():
	dic = request.form;
	added = dic["reviewed"].split(',');
	removed = dic["removed"].split(',');
	for vid in added:
		if len(vid)==0:
			break;
		q="insert into VideoReview (videoID, reviewed) values (%s, TRUE)"%vid;
		g.cursor.execute(q);
		g.conn.commit();
	for did in removed:
		if len(did)==0:
			break;
		q= "delete from video where id=%s"%did;
		g.cursor.execute(q);
		g.conn.commit();

	return make_response("OK");
	

@app.route("/swap/<int:id1>/<int:id2>")
def swap(id1, id2):
	q1 = "update AlbumReview set id=999 where id=%s"%id1;
	q2 = "update AlbumReview set id=%s where id=%s"%(id1,id2);
	q3 = "update AlbumReview set id=%s where id=999"%id2;
	
	g.cursor.execute(q1);
	g.conn.commit();
	g.cursor.execute(q2);
	g.conn.commit();
	g.cursor.execute(q3);
	g.conn.commit();

	return "Done!";
	
@app.route("/editmessage")
def editMessage():
	return render_template('edit.html');	

def downloadImage(url, filePath):
	print "Handling %s"%url;
	u = urllib2.urlopen(url);
	localFile = open(filePath, 'w');
	localFile.write(u.read());
	localFile.close();
		
def generateThumbnail(imgFile, thumbFile):
	im = Image.open(imgFile);
	(width, height) = im.size;
	thumbwidth = 150;
	thumbheight = thumbwidth*height/width;
	im.thumbnail((thumbwidth, thumbheight), Image.ANTIALIAS);
	im.save(thumbFile, "JPEG", quality=95);
	return (width, height);

def addDBPhoto(album_id, URL, index, checksum, filepath, thumbpath, width, height):
        g.cursor.execute("insert into Photo (filePath,thumbnailPath, signature) values('%s','%s','%s')"% (filepath, thumbpath, checksum));
        g.conn.commit();
        g.cursor.execute("select last_insert_id()");
        photoid = g.cursor.fetchone()[0];
        g.cursor.execute("insert into PhotoURL (photoID, URL) values (%s, '%s')"%(photoid, URL));
        g.conn.commit();
        g.cursor.execute("insert into PhotoAlbum (photoID, albumID, idx) values (%s, %s, %s)"%(photoid,album_id, index));
        g.conn.commit();
        g.cursor.execute("insert into PhotoSize (photoID, width, height) values(%s, %s, %s)"%(photoid, width, height));
        g.conn.commit();

@app.route("/postmessage", methods = ["POST"])
def postMessage():
	#for each of the urls, download the image, generate the thumbnails and put into right place

	print request.form;
	urlstr = request.form["urls"];	
	urls = urlstr.split(',');
	msg = request.form["msg"];


	PathPrefix = "/tmp/";
	ThumbPrefix = "/home/ubuntu/thumbnail/"
	while True:
		identifier = "msg"+ str(random.randint(0,65535));
		if not os.path.exists(PathPrefix+identifier):
			break;
	path = PathPrefix+identifier;
	thumbPath = ThumbPrefix+identifier;
	os.mkdir(path);
	os.mkdir(thumbPath);

	# create album in Db
	count = len(urls);
	stmt = "insert into Album (identifier, URL,imageCount) Values ('%s', '', %d)"%(identifier, count);
	g.cursor.execute(stmt);
	g.conn.commit();
	
	g.cursor.execute("select last_insert_id()");
        albumID = g.cursor.fetchone()[0];
	
	for i in range(0, len(urls)):
		filePath = path + "/%d.jpg"%i;	
		downloadImage(urls[i], filePath);
		thumbFilePath = thumbPath + "/%d.jpg"%i;
		(width, height)=generateThumbnail(filePath, thumbFilePath);
		# add the photo into db
		addDBPhoto(albumID, urls[i], i, "", filePath, thumbFilePath, width, height);
		
	#get the AlbumReview ID
	stmt = "insert into AlbumReview (albumID, reviewed, level, cut) values (%s, TRUE, 0, %d)"%(albumID, count);
	g.cursor.execute(stmt);
	g.conn.commit();
	g.cursor.execute("select last_insert_id()");
        reviewID = g.cursor.fetchone()[0];
	
	#add the message record with text message and albumReview ID
	deviceStmt = "select id from Device";
	g.cursor.execute(deviceStmt);
	records = g.cursor.fetchall();
	if not records:
		return jsonify(error="no registered device");
	for record in records:
		deviceID = record[0];
		nowstr = datetime.now().strftime('%Y-%m-%d %H:%M:%S');
		msgStmt = "insert into Message (deviceID, isSent, isRead, messageText, parameter, createdOn) values (%s, FALSE, FALSE, '%s', '%s', '%s')"%(deviceID, msg, reviewID, nowstr);
		print msgStmt;
		g.cursor.execute(msgStmt);
		g.conn.commit();
		
	return make_response("OK");	
	

if __name__ == '__main__':
	app.debug=True;
	app.run(host='0.0.0.0')
