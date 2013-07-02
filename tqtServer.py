from flask import Flask, request, jsonify, make_response,redirect,g
import MySQLdb
from datetime import datetime, timedelta
import time;
import random;
import json;
import memcache;

app = Flask(__name__)
app.debug = False

@app.before_request
def before_request():
#	g.timer = time.time()*1000;
#	app.logger.debug("Start: %s"%g.timer);
	g.conn = MySQLdb.connect(db="TONGQUETAI", user="root", passwd="123456", charset="utf8");
	g.cursor = g.conn.cursor();

@app.teardown_request
def teardown_request(exception):
	g.conn.close();

#	span = time.time()*1000 - g.timer;
#	app.logger.debug("End %s:%s milliseconds"%(g.timer,span));	

def validateKey(key):
	return key=="pass";

def getKeycode():
	return "pass";

@app.route("/ref/<source>")
def refer(source):
	iTunesURL = "https://itunes.apple.com/cn/app/ku-tu/id580476189?mt=8";
	q = "update REF set count=count+1 where source='%s'"%source;
	g.cursor.execute(q);
	g.conn.commit();
	return redirect(iTunesURL);

def getRandomScore():
	i = random.randint(32,48);
	return (i/10.0);

@app.route("/albums")
def getDefaultAlbums():
	#obtain the default sequence number
	getSeqStmt = "select startSeq from Seq;"
	g.cursor.execute(getSeqStmt);
	defaultSeq = g.cursor.fetchone()[0];	

#	return jsonify(seq=defaultSeq);
	return getAlbums(defaultSeq);

def getThumbnailURLFromPath(path):
	root = "http://www.tongque.net.cn/thumbnail/";
	return root+path[15:];

@app.route("/album")
def getAlbumInfo():
	key = request.args["key"];
        isValid = validateKey(key);

	# Album ids are in header
#	headers = request.headers;
	idstr = request.args["favIDs"];
	ids = idstr.split('|');
	

	albums = {};
	for aID in ids:
		#print "ID is ************ "+ aID;
		getAlbumStmt = "select AlbumReview.id, AlbumReview.albumID, AlbumReview.cut, Album.imageCount from AlbumReview, Album  where Album.id=AlbumReview.albumID and AlbumReview.reviewed=TRUE and AlbumReview.id=%s"%aID;
		g.cursor.execute(getAlbumStmt);
		record = g.cursor.fetchone();

		reviewID = record[0];
                albumID = record[1];
                cutNumber = int(record[2]);
                imgCount = record[3];
		
		#Get score
		getScoreStmt = "select AlbumInfo.score from AlbumInfo where AlbumInfo.albumID=%s"%albumID;
		g.cursor.execute(getScoreStmt);
		scoreRecord = g.cursor.fetchone();
		if scoreRecord:
			score = scoreRecord[0];
		else:
			score = getRandomScore();

		thumbnails = [];
                imgURLs = [];
                imgSizes = [];
                getPhotosStmt = "select Photo.thumbnailPath, PhotoURL.URL, PhotoAlbum.idx, PhotoSize.width, PhotoSize.height from Photo, PhotoAlbum, PhotoURL, PhotoSize where PhotoAlbum.albumID=%s and PhotoAlbum.photoID=Photo.id and PhotoAlbum.photoID=PhotoURL.photoID and PhotoAlbum.photoID=PhotoSize.photoID ORDER BY PhotoAlbum.idx "%albumID;
		g.cursor.execute(getPhotosStmt);
		photoRecords = g.cursor.fetchall();
		
		if isValid:
                        last = len(photoRecords);
                else:
                        last = cutNumber;
                for i in range(0, last):
                        photoRecord = photoRecords[i];
                        thumbnail = getThumbnailURLFromPath(photoRecord[0]);
                        thumbnails.append(thumbnail);
                        url = photoRecord[1];
                        imgURLs.append(url);
                        photoSize = (photoRecord[3], photoRecord[4]);
                        imgSizes.append(photoSize);
		album = {
                        "ID": reviewID,
                        "imgCount": imgCount,
                        "cut": cutNumber,
                        "thumbnail": thumbnails[0],
                        "thumbnails": thumbnails,
                        "imgURLs": imgURLs,
                        "imgSizes": imgSizes,
			"score": str(score)
                };
		albums[aID]= album;
	#print jsonify(**albums);
	return jsonify(**albums);

@app.route("/videos")
def getDefaultVideos():
        getSeqStmt = "select startVideo from Seq;"
        g.cursor.execute(getSeqStmt);
        defaultSeq = g.cursor.fetchone()[0];

        return getVideos(defaultSeq);

@app.route("/videos/<seq>")
def getVideos(seq):
	LIMIT=10;
	query = "select VideoReview.id, identifier, videoURL from video, VideoReview where VideoReview.id<=%s and VideoReview.videoID=video.id order by VideoReview.id DESC limit %d"%(seq, LIMIT);
	g.cursor.execute(query);
	records = g.cursor.fetchall();
	
	videos = [];
	for record in records:
		thumburl = "http:/tongque.net.cn/video/%s.jpg"%record[1];
		video = {
			"ID":record[0],
			"thumbnail": thumburl,
			"videourl": record[2]
		};
		videos.append(video);
	batch = {
		"videos": videos,
		"firstID": videos[0]["ID"],
		"lastID": videos[-1]["ID"]-1
	};
	return jsonify(**batch);

@app.route("/albums/<seq>")
def getAlbums(seq):

#	g.timer = time.time()*1000;
#	sec = int(time.time());
#	app.logger.debug("InALBUMS: %s, sec: %d"%(g.timer,sec));
	#check if the passed key is authenticated
	key = request.args["key"];
	isValid = validateKey(key);

	mc = memcache.Client(['127.0.0.1:11211'], debug=0)
	if isValid:
		mckey = "albums-%s-full"%str(seq);
	else:
		mckey = "albums-%s"%str(seq);
	
	#app.logger.debug(mckey);	
	obj = mc.get(mckey);
	if obj:
		return jsonify(**obj);
	else:	
		obj = getAlbumsFromDB(seq, isValid);
		mc.set(mckey, obj);
		return jsonify(**obj);

def getAlbumsFromDB(seq, isValid):
	LIMIT = 20;
	getAlbumsStmt = "select AlbumReview.id, AlbumReview.albumID, AlbumReview.cut, Album.imageCount from Album, AlbumReview where Album.id=AlbumReview.albumID and AlbumReview.reviewed=TRUE and AlbumReview.id<%s ORDER BY AlbumReview.id DESC LIMIT %d "%(seq, LIMIT);
	g.cursor.execute(getAlbumsStmt);
	records = g.cursor.fetchall();
	albums = [];
#	print len(records);
	for record in records:
		reviewID = record[0];
		albumID = record[1];
		cutNumber = int(record[2]);
		imgCount = record[3];
		
                #Get score
                getScoreStmt = "select AlbumInfo.score from AlbumInfo where AlbumInfo.albumID=%s"%albumID;
                g.cursor.execute(getScoreStmt);
                scoreRecord = g.cursor.fetchone();
                if scoreRecord:
                        score = scoreRecord[0];
                else:
                        score = getRandomScore();
		
		thumbnails = [];
		imgURLs = [];
		imgSizes = [];
		getPhotosStmt = "select Photo.thumbnailPath, PhotoURL.URL, PhotoAlbum.idx, PhotoSize.width, PhotoSize.height from Photo, PhotoAlbum, PhotoURL, PhotoSize where PhotoAlbum.albumID=%s and PhotoAlbum.photoID=Photo.id and PhotoAlbum.photoID=PhotoURL.photoID and PhotoAlbum.photoID=PhotoSize.photoID ORDER BY PhotoAlbum.idx "%albumID;
		g.cursor.execute(getPhotosStmt);
		photoRecords = g.cursor.fetchall();
		
		if isValid:
			last = len(photoRecords);
		else:
			last = cutNumber;
		for i in range(0, last):
			photoRecord = photoRecords[i];
			thumbnail = getThumbnailURLFromPath(photoRecord[0]);
			thumbnails.append(thumbnail);
			url = photoRecord[1];
			imgURLs.append(url);
			photoSize = (photoRecord[3], photoRecord[4]);
			imgSizes.append(photoSize);
		
		#print reviewID;
		album = {
			"ID": reviewID,
			"imgCount": imgCount,
			"cut": cutNumber,
			"thumbnail": thumbnails[0],
			"thumbnails": thumbnails,
			"imgURLs": imgURLs,
			"imgSizes": imgSizes,
			"score": str(score)
		}
		albums.append(album);
	batch = {
		"albums": albums,
		"nextID": albums[-1]["ID"]-1,
		"firstID": albums[0]["ID"]
	}
#	span = time.time()*1000 - g.timer;
#	app.logger.debug("OUT %s:%s milliseconds"%(g.timer,span));	
#	print jsonify(**batch);
	return batch;
#	return jsonify(result='OK');

def formatDate(dt):
	return dt.strftime('%Y-%m-%d %H:%M:%S')

def formatDateDay(dt):
	return dt.strftime('%Y-%m-%d')
	

@app.route("/credits")
def getCredits():
	deviceID = request.args["deviceID"];
	getCreditsStmt = "select Credit.credit from Credit, Device where Device.identifier='%s' and Credit.deviceID=Device.id"%deviceID;
	g.cursor.execute(getCreditsStmt);
	record = g.cursor.fetchone();
	if record:
		credit = record[0];
	else:
		credit = -1;
	return jsonify(credit=credit);



@app.route("/auth", methods=["POST"])
def authenticate():
	# Different scenarios:
	# 1. the device has not been registered
	# 2. the device has been registered, but not a member
	# 3. the device has been registered, is a member, but expires
	# 4. the device has been registered, is a valid member now.
	# Should return different responses for each scenario
	
	#get deviceID from request and check if is member
	#return a keycode
	assert request.method == "POST";
	deviceID = request.form["deviceID"];
	token = request.form["token"];
	
	#first check if device table contains this device
	stmt1 = "select id from Device where identifier='%s'"%deviceID;
	g.cursor.execute(stmt1);
	row = g.cursor.fetchone();
	# if the device has not been registered, return as such
	if not row:
		dID=registerDevice(deviceID);
	else:
		dID = row[0];

	# update the device token first
	stmt3 = "update Device set token='%s' where id=%s"%(token, dID);
	g.cursor.execute(stmt3);
	g.conn.commit();

	recordAction(deviceID,"logIn" ,"login");

	stmt2 = "select * from Membership where deviceID=%s"%dID;
	g.cursor.execute(stmt2);
	row = g.cursor.fetchone();
	# if the device is not a member
	if not row:
		return jsonify(registered=1, isMember=0);
	else:
		keycode = getKeycode();
		return jsonify(registered=1, isMember=1, key=keycode);
#	expireDate = row[0];
#	now = datetime.now();
	# if the device is an expired member
#	if now > expireDate:
#		return jsonify(registered=1, isMember=1, memberValid=0);
		
	# A valid member
#	expireDateDay = formatDateDay(expireDate);
#	return jsonify(registered=1, isMember=1, memberValid=1, key=keycode, expire=expireDateDay);
	
#@app.route("/register", methods = ["POST"])
def registerDevice(deviceID):
#	deviceID = request.form["deviceID"];
#	token = request.form["token"];
#	stmt1 = "select * from Device where identifier='%s'"%deviceID;
#        g.cursor.execute(stmt1);
#        row = g.cursor.fetchone();
        # if the device has been registered, return as such
#        if row:
#                return jsonify(registered=1);
	# register the device and its token
	stmt2 = "insert into Device (identifier, token, isActive, attachedToAccount) values ('%s','', TRUE, FALSE)"%(deviceID);
	g.cursor.execute(stmt2);
	g.conn.commit();
	
	stmt4 = "select id from Device where identifier='%s'"%deviceID;
	g.cursor.execute(stmt4);
	record = g.cursor.fetchone();
	newID = record[0];
	
	# give the device initial credit
	initialCredit = 200;
	stmt3 = "insert into Credit (deviceID, credit) values (%s, %d)"%(newID, initialCredit);
	g.cursor.execute(stmt3);
	g.conn.commit();
	return newID;
	
@app.route("/purchase", methods = ["POST"])
def purchase():
	deviceID = request.form["deviceID"];
        purchaseType = int(request.form["type"]);
	
	stmt0 = "select id from Device where identifier='%s'"%deviceID;
        g.cursor.execute(stmt0);
        row = g.cursor.fetchone();
        if not row:
                return jsonify(error="not registered");
        deviceID = row[0];
	
	# record the purchase operation
	now = formatDate(datetime.now());
	stmt1 = "insert into Purchase (deviceID, purchaseDate, purchaseType) values(%s, '%s', %s)"%(deviceID, now, purchaseType);
	g.cursor.execute(stmt1);
	g.conn.commit();

	#add the credit
	creditStmt = "select credit from Credit where deviceID=%s"%deviceID;
        g.cursor.execute(creditStmt);
        result = g.cursor.fetchone();
       	
	creditMapping = [600,3600,6000];
	diff = creditMapping[purchaseType];
	if not result:
		# if record not found, add the record
		stmt = "insert into Credit (deviceID, credit) values (%s, %s)"%(deviceID, diff);
		g.cursor.execute(stmt);
		g.conn.commit();
		newCredit = diff;
	else:
		creditvalue=int(result[0]);
		newCredit = creditvalue+diff;
         	#update the credit value
        	updateCreditStmt = "update Credit set credit=credit+%d where deviceID=%s"%(diff, deviceID);
        	g.cursor.execute(updateCreditStmt);
		g.conn.commit();
	
	return jsonify(success=1, credit=newCredit);
	

@app.route("/join", methods = ["POST"])
def joinMembership():
	deviceID = request.form["deviceID"];
	joinType = int(request.form["joinType"]);
	
	#with credit 	0 for month, 1 for half year, 2 for year
	stmt0 = "select id from Device where identifier='%s'"%deviceID;
	g.cursor.execute(stmt0);
	row = g.cursor.fetchone();
	if not row:
		return jsonify(error="not registered");
	deviceID = row[0];
	
	creditStmt = "select credit from Credit where deviceID=%s"%deviceID;
	g.cursor.execute(creditStmt);
	result = g.cursor.fetchone();
	if len(result)==0:
		return jsonify(error="no credit");
	creditvalue=int(result[0]);

	if joinType==1:
		typeStr = "credit";
		creditsNeeded = 600;
		# If purchase with credit, check if credit is enough
		if creditvalue<creditsNeeded:
			return jsonify(error="not enough credit");
		# substract the credit value
		updateCreditStmt = "update Credit set credit=credit-%d where deviceID=%s"%(creditsNeeded, deviceID);
		g.cursor.execute(updateCreditStmt);
		g.conn.commit();
		creditvalue = creditvalue - creditsNeeded;
	else:
		typeStr = "purchase";
	
	now = datetime.now();
	stmt2 = "insert into Membership (type,deviceID,expireDate) values('%s',%s, '%s')"%(typeStr, deviceID, formatDate(now));
#	stmt2 = "select expireDate from Membership where deviceID=%s"%deviceID;
	g.cursor.execute(stmt2);
	g.conn.commit();
	return jsonify(success=1, credit=creditvalue);
#	row = g.cursor.fetchone();
	
	# the membership type
#	days = 0;
#	if joinType == 0: #month
#		days = 31;
#	elif joinType == 1: #half-year
#		days = 183;
#	elif joinType == 2: #whole year
#		days = 365;
		
	# if currently not a member, add member
#	now = datetime.now();
#	if not row:
#		then = now + timedelta(days=days);
#		stmt3 = "insert into Membership (deviceID, expireDate) values(%s, '%s')"%(deviceID, formatDate(then));
#		g.cursor.execute(stmt3);
#		g.conn.commit();
#	else:
#		expireOn = row[0];
		# if currently a member, but expired, set expiration date relative to now
#		if expireOn < now:
#			then = now+ timedelta(days = days);
		# if currently a valid member, set expiration date relative to expiration date
#		else:
#			then = expireOn + timedelta(days=days);
#		stmt4 = "update Membership set expireDate='%s' where deviceID=%s"%(formatDate(then), deviceID);
#		g.cursor.execute(stmt4);
#		g.conn.commit();
	
#	return jsonify(success=1, credit=newCredit);

def addCredit(deviceID, earning):
	stmt = "update Credit set credit=credit+%d where deviceID=(select id from Device where identifier='%s')"%(earning,deviceID);
	g.cursor.execute(stmt);
	g.conn.commit();

def recordAction(deviceID, action, parameter):
	query = "select id from Device where identifier='%s'"%deviceID;
	g.cursor.execute(query);
	result = g.cursor.fetchone();	
	dID = result[0];
	
	now = formatDate(datetime.now());
	
	insertStmt = "insert into Action (deviceID, action, parameter, time) values (%s, '%s', '%s', '%s')"%(dID, action, parameter, now);
	g.cursor.execute(insertStmt);
	g.conn.commit();

@app.route("/rate",methods=["POST"])
def rate():
	deviceID = request.form["deviceID"];
	albumID = request.form["albumID"];
	score = float(request.form["score"]);
	
	if score<0 or score>5:
		return jsonify(error="score not in range");

	query = "select albumID from AlbumReview where id=%s"%albumID;
	g.cursor.execute(query);
	result = g.cursor.fetchone();
	
	if not result:
		return jsonify(error="id not correct");
	
	albumID = result[0];
	query1 = "select score from AlbumInfo where albumID=%s"%albumID;
	g.cursor.execute(query1);
	result = g.cursor.fetchone();
	
	if not result:
		# if no score, take this as initial score
		insertStmt = "insert into AlbumInfo (albumID, score) values ('%s', %f)"%(albumID, score);
		g.cursor.execute(insertStmt);
		g.conn.commit();
	else:
		oldscore = float(result[0]);
		# the algorithm here is to take 1/10 of the difference and add it to old score
		diff = (score-oldscore)/10;
		newscore = oldscore+diff;
		updateStmt = "update AlbumInfo set score=%f where albumID=%s"%(newscore,albumID);
		g.cursor.execute(updateStmt);
		g.conn.commit();
	
	#Now update the credit value of user
	#rateCredit = 5;
	#addCredit(deviceID, rateCredit);
	
	#Record the action
	parameter = "%s:%f"%(albumID,score);
	recordAction(deviceID, "rate", 	parameter);
	
	return jsonify(addCredit=rateCredit);

@app.route('/starlist')
def starlist():
        query = "select * from Star order by vote DESC LIMIT 15";
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

@app.route('/view', methods=["POST"])
def view():
	deviceID = request.form["deviceID"];
       	parameter = request.form["parameter"];
	recordAction(deviceID, "view", parameter);
	return jsonify(result="OK");

@app.route('/follow', methods=["POST"])
def follow():
	deviceID = request.form["deviceID"];
	starid = request.form["starID"];
	parameter = "%s"%starid;
        recordAction(deviceID, "follow", parameter);

        return jsonify(result="OK");

@app.route('/apply', methods=["POST"])
def applyGirl():
        deviceID = request.form["deviceID"];
        nick = request.form["nick"];
        parameter = "%s"%nick;
        recordAction(deviceID, "apply", parameter);

        return jsonify(result="OK");
	

@app.route("/sharephoto", methods=["POST"])
def sharePhoto():
	deviceID = request.form["deviceID"];
	albumID = request.form["albumID"];
	photoIdx = request.form["index"];
	shareVia = request.form["via"];
	
	# update the credit value
	shareCredit = 10;
	addCredit(deviceID, shareCredit);
	#Record the action
	parameter = "%s:%s:%s"%(albumID, photoIdx, shareVia);
	recordAction(deviceID, "share", parameter);
	
	return jsonify(addCredit=shareCredit);

@app.route("/shareapp", methods=["POST"])
def shareApp():
	deviceID = request.form["deviceID"];
        shareVia = request.form["via"];

        # update the credit value
        shareCredit = 100;
        addCredit(deviceID, shareCredit);
        #Record the action
        parameter = shareVia;
        recordAction(deviceID, "shareApp", parameter);

        return jsonify(addCredit=shareCredit);

@app.route("/save",methods=["POST"])
def savephoto():
	deviceID = request.form["deviceID"];
	albumID = request.form["albumID"];
        photoIdx = request.form["index"];
	
	parameter = "%s:%s"%(albumID,photoIdx);
	recordAction(deviceID, "save", parameter);
	
	return jsonify(result="OK");

@app.route("/fav", methods=["POST"])
def favAlbum():
	deviceID = request.form["deviceID"];
	albumID = request.form["albumID"];
	
	parameter = albumID;
	recordAction(deviceID, "fav", parameter);
	
	return jsonify(result="OK");

@app.route("/report", methods=["POST"])
def reportAlbum():
        deviceID = request.form["deviceID"];
        albumID = request.form["albumID"];

        parameter = albumID;
        recordAction(deviceID, "report", parameter);

        return jsonify(result="OK");

@app.route("/getmsg")
def getMessages():	
	deviceID = request.args["deviceID"];
	query = "select id from Device where identifier='%s'"%deviceID;
        g.cursor.execute(query);
        result = g.cursor.fetchone();
        dID = result[0];

	recordAction(deviceID, "getMessage",  "NULL");

	query = "select id, messageText, parameter, createdOn from Message where deviceID=%s and isRead=FALSE ORDER BY createdOn"%dID;
	g.cursor.execute(query);
	records = g.cursor.fetchall();

	if not records:
		return jsonify(count=0);
	
	messages = [];
	for record in records:
		msgID = record[0];
		text = record[1];
		parameter = record[2];
		createdOn = formatDateDay(record[3]);
		message = {
			"id": msgID,
			"text":text,
			"parameter": parameter,
			"createdOn": createdOn
		}
		messages.append(message);
	result = {
		"count": len(records),
		"messages": messages
	};
	return jsonify(**result);

@app.route("/readmsg", methods=["POST"])
def readMessage():
	msgID = request.form["msgID"];
	updateStmt = "update Message set isRead=TRUE where id=%s"%msgID;
	g.cursor.execute(updateStmt);
	g.conn.commit();
	
	return jsonify(result="OK");

@app.route("/bindAccount", methods=["POST"])
def bindAccount():
	deviceID = request.form["deviceID"];
	accountType = request.form["type"];
	account = request.form["account"];
	
	query = "select id from Device where identifier='%s'"%deviceID;
        g.cursor.execute(query);
        result = g.cursor.fetchone();
        dID = result[0];

	query = "select * from Account where deviceID=%s and type='%s'"%(dID, accountType);
	g.cursor.execute(query);
	result = g.cursor.fetchone();
	
	#if account exists, update; else insert
	if not result:
		stmt = "insert into Account (deviceID, type, account) values (%s, '%s', '%s')"%(dID, accountType, account);
		g.cursor.execute(stmt);
		g.conn.commit();
	else:
		stmt = "update Account set account=%s where deviceID='%s' and type='%s'"%(account, dID, accountType);
		g.cursor.execute(stmt);
		g.conn.commit();
	
	return jsonify(result="OK");
	
@app.route("/friends", methods=["POST"])
def addFriends():
	deviceID = request.form["deviceID"];
	friendstr = request.form["friends"];
	friends = friendstr.split(';');
#	friends = json.loads(friendstr);
        
	query = "select id from Device where identifier='%s'"%deviceID;
        g.cursor.execute(query);
        result = g.cursor.fetchone();
        dID = result[0];

	for friend in friends:
		app.logger.debug(friend);		
		if len(friend)<5:
			continue;
		fid = friend.split(':')[0];
		fname = friend.split(':')[1];
		stmt = "insert into Friends (deviceID, friendID, friendName) values(%s, '%s', '%s')"%(dID, fid, fname);
		g.cursor.execute(stmt);
		g.conn.commit();
	
	return make_response("OK");

if __name__ == '__main__':
	app.debug=True;
	app.run(host='0.0.0.0')

