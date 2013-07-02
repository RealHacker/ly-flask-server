# This script should be scheduled to execute periodically to send push notifications to clients
from pyapns import configure, provision, notify, feedback
import MySQLdb

configure({'HOST': 'http://localhost:7077/'})
provision('tqt', open('KutuProduction.pem').read(), 'production')
# Get all the active deviceIDs
db = MySQLdb.connect(db="TONGQUETAI", user="root", passwd="123456", charset="utf8");
cursor = db.cursor();

query = "select id, token from Device where isActive=TRUE";
cursor.execute(query);
devices = cursor.fetchall();

for device in devices:
	deviceToken = device[1];
	deviceID = device[0];
	# Query the messages for this device
	unReadQuery = "select count(*) from Message where deviceID=%s and isRead=FALSE"%deviceID;
	cursor.execute(unReadQuery);
	result = cursor.fetchone();
	unRead = int(result[0]);
	
	if unRead==0:
		continue;
	# Send the most recent unsent message
	msgQuery = "select id,messageText from Message where deviceID=%s and isSent=FALSE ORDER BY createdOn DESC"%(deviceID);
	cursor.execute(msgQuery);
	msgs = cursor.fetchall();
	if not msgs:
		#Only send badge numbers
		notify('tqt', deviceToken, {'aps':{'badge': unRead, 'sound':'default'}});
		print "Send message to %s with no alert and badge %d"%(deviceToken, unRead);
	else:	
		alertMsg = msgs[0][1];
		notify('tqt', deviceToken, {'aps':{'badge':unRead,'alert': alertMsg, 'sound': 'default'}});
		print "Send message to %s"%deviceToken;
		print "Message: "+alertMsg;
		print "unread count: %d"%unRead;
		#Then set the unsent messages as sent
		for msg in msgs:
			msgID = msg[0];
			setQuery = "update Message set isSent=TRUE where id=%s"%msgID;
			cursor.execute(setQuery);
			db.commit();

# Record the inactive clients
inactives = feedback('tqt');
for inactive in inactives:
	time = inactive[0];
	token = inactive[1];
	print "On %s, token %s becomes inactive"%(time, token);
	stmt = "update Device set isActive=FALSE where token='%s'"%token;
	cursor.execute(stmt);
	db.commit();
