#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
from flask_bootstrap import Bootstrap 
import hashlib
import os
import time

#Initialize the app from Flask
app = Flask(__name__)
app._static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates/static")
Bootstrap(app) #for bootstrap 

#Configure MySQL

conn = pymysql.connect(host='localhost',
                       port=8889,
                       user='root',
                       password='root',
                       db='PriCoSha',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)




#Define a route to hello function
@app.route('/')
def hello():
	return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
	return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
	return render_template('register.html')
#Define route for friendgroup
@app.route('/friendgroup')
def friendgroupRoute():
	return render_template('friendgroup.html')

@app.route('/changeuser')
def changeuserRoute():
	return render_template('changeuser.html')

@app.route('/changepass')
def changepassRoute():
	return render_template('changepass.html')

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
	#grabs information from the forms
	username = request.form['username']
	password = hashlib.sha1(request.form['password']).hexdigest()
	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM Person WHERE username = %s and password = %s'
	cursor.execute(query, (username, password))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	cursor.close()
	error = None
	if(data):
		#creates a session for the the user
		#session is a built in
		session['username'] = username
		return redirect(url_for('home'))
	else:
		#returns an error message to the html page
		error = 'Invalid login or username'
		return render_template('login.html', error=error)
		

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
	#grabs information from the forms
	username = request.form['username']
	password = hashlib.sha1(request.form['password']).hexdigest()
	firstname = request.form['firstname']
	lastname = request.form['lastname']

	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM Person WHERE username = %s'
	cursor.execute(query, (username))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	error = None
	if(data):
		#If the previous query returns data, then user exists
		error = "This user already exists"
		return render_template('register.html', error = error)
	else:
		ins = 'INSERT INTO Person VALUES (%s, %s, %s, %s)'
		cursor.execute(ins, (username, password, firstname, lastname))
		conn.commit()
		cursor.close()
		return render_template('index.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
	username = session['username']
	cursor = conn.cursor()
	#get posts this user should be seeing
	query = 'SELECT id, username, timest, content_name, public FROM Content WHERE id IN \
	(SELECT id FROM Member NATURAL JOIN Share WHERE Member.username = %s) OR public = 1 OR username = %s OR \
	id IN (SELECT id FROM Tag WHERE username_taggee = %s AND status = 1) \
	OR %s in (SELECT username FROM Member WHERE group_name IN \
	(SELECT group_name FROM Member WHERE username=%s)) ORDER BY timest DESC'

	cursor.execute(query, (username, username, username, username, username))
	data = cursor.fetchall()
	cursor.close()

	#get posts that the user was tagged in that they have not approved yet
	cursor = conn.cursor()
	query = 'SELECT id, username, timest, content_name FROM Content WHERE id IN (SELECT id FROM Tag WHERE username_taggee = %s AND status = 0)'
	cursor.execute(query, (username))
	managetags = cursor.fetchall()
	cursor.close()

	#get tag information for all posts
	cursor = conn.cursor()
	query = 'SELECT id, username_taggee FROM Tag WHERE status = 1'
	cursor.execute(query)
	tagData = cursor.fetchall()
	cursor.close()

	#get comment information for all posts
	cursor = conn.cursor() 
	query = 'SELECT id, username, comment_text, timest FROM Comment'
	cursor.execute(query)
	commentData = cursor.fetchall()
	cursor.close()

	#groups that user is owner of
	cursor = conn.cursor()
	query = 'SELECT DISTINCT group_name, username_creator FROM Member WHERE username_creator = %s'
	cursor.execute(query, (username))
	fgownerdata = cursor.fetchall()
	cursor.close()

	#groups that user is member of
	cursor = conn.cursor()
	query = 'SELECT DISTINCT group_name FROM Member WHERE username = %s'
	cursor.execute(query, (username))
	fgmemberdata = cursor.fetchall()
	cursor.close()

	tagged = ""
	contentID = ""
	for key in request.form:
		if key == 'tags':
			tagged = request.form[key]
		if key == 'idClicked':
			contentID = request.form[key]
	if (tagged != "" and contentID != ""):
		cursor = conn.cursor() 
		checker = 'SELECT * FROM Tag WHERE id = %s AND username_tagger = %s AND username_taggee = %s'
		cursor.execute(checker, (contentID, username, tagged))
		checked = cursor.fetchone()
		error = None
		if (checked):
			error = "This user is already tagged"
			return render_template('home.html', username=username, posts=data, tagData=tagData, managetags=managetags, commentData=commentData, fgmemberdata=fgmemberdata, fgownerdata=fgownerdata, error = error)
		cursor.close()

		cursor = conn.cursor()
		query = 'INSERT INTO Tag (id, username_tagger, username_taggee, timest, status) VALUES (%s, %s, %s, %s, %s)'
		cursor.execute(query, (contentID, username, tagged, time.strftime('%Y-%m-%d %H:%M:%S'), 0))
		conn.commit()
		cursor.close()

	#render home.html and pass info info the html for parsing
	return render_template('home.html', username=username, posts=data, tagData=tagData, managetags=managetags, fgmemberdata=fgmemberdata, fgownerdata=fgownerdata, commentData=commentData)

		
@app.route('/post', methods=['GET', 'POST'])
def post():
	username = session['username']
	cursor = conn.cursor() 
	content = request.form['content']
	public = request.form['pubPriv'] 
	filepath = request.form['filepath']

	if (public == "True"):
		public = True
	else:
		public = False

	query = 'INSERT INTO content (content_name, username, file_path, public) VALUES (%s, %s, %s, %s)'

	cursor.execute(query, (content, username, filepath, public))

	maxValQuery = 'SELECT MAX(id) FROM Content'
	cursor.execute(maxValQuery)
	maxVal = cursor.fetchone()
	maxVal = maxVal['MAX(id)']

	if (public == False):
		groupNames = request.form['groupNames']
		listOfGroupNames = groupNames.split(',')
		cursor = conn.cursor()
		for group in listOfGroupNames:
			print(group)
			query = 'INSERT INTO Share (id, group_name, username) VALUES (%s, %s, %s)'
			cursor.execute(query, (maxVal, group, username))
		

	conn.commit()
	cursor.close()
	return redirect(url_for('home'))

@app.route('/approvetag/<contentID>')
def approvetag(contentID):
	username = session['username']
	cursor = conn.cursor()
	query = 'UPDATE Tag SET status = 1 WHERE id = %s AND username_taggee = %s'
	cursor.execute(query, (contentID, username))
	conn.commit()
	cursor.close()
	return redirect(url_for('home'))

@app.route('/rejecttag/<contentID>')
def rejecttag(contentID):
	username = session['username']
	cursor = conn.cursor()
	query = 'DELETE FROM Tag WHERE id = %s AND username_taggee = %s'
	cursor.execute(query, (contentID, username))
	conn.commit()
	cursor.close()
	return redirect(url_for('home'))

@app.route('/deletepost/<contentID>')
def deletepost(contentID):
	username = session['username']
	cursor = conn.cursor()
	query = 'DELETE FROM Content WHERE id = %s'
	cursor.execute(query, (contentID))
	conn.commit()
	cursor.close()
	return redirect(url_for('home'))

# @app.route('/friendGroupAuth')
# def friendGroupAuth():
# 	# groupname = session['groupname']
# 	# username = session['username']
# 	# description = session ['description']
# 	# cursor = conn.cursor() 
# 	# query = 'INSERT INTO FriendGroup VALUES (%s, %s, %s)'
# 	# conn.commit()
# 	# cursor.close()
# 	return redirect(url_for('home'))

@app.route('/friendGroupAuth', methods=['GET','POST'])
def friendGroupAuth():
	username = session['username']
	cursor = conn.cursor() 
	groupname = request.form['groupname']
	description = request.form['desc']
	#create friendgroup and set curr username as owner
	query = 'INSERT INTO FriendGroup (group_name, username, description) VALUES (%s, %s, %s)'
	cursor.execute(query, (groupname, username, description))
	for key in request.form:
		if key.startswith('Member'):
			#add each member to the DB
			query = 'INSERT INTO Member (username, group_name, username_creator) VALUES (%s, %s, %s)'
			cursor.execute(query, (request.form[key], groupname, username))
			#print(request.form[key] will print the usernames entered for all members)
	
	conn.commit()
	cursor.close()
	return redirect(url_for('home'))

@app.route('/changeuser', methods=['GET', 'POST'])
def changeuser():
	username = session['username']
	cursor = conn.cursor() 
	changeuser = request.form['changeuser']
	query = 'UPDATE Person SET username = %s WHERE username = %s'
	cursor.execute(query, (changeuser, username))
	conn.commit()
	cursor.close()
	session['username'] = changeuser
	return redirect(url_for('home'))

@app.route('/changepass', methods=['GET', 'POST'])
def changepass():
	username = session['username']
	currentpass = hashlib.sha1(request.form['currentpass']).hexdigest()
	changepass = hashlib.sha1(request.form['newpass']).hexdigest()
	cursor = conn.cursor()
	query = 'SELECT * FROM Person WHERE password = %s'
	cursor.execute(query, currentpass)
	passdata = cursor.fetchone()
	cursor.close()
	error = None
	if (passdata):
		cursor = conn.cursor()
		query = 'UPDATE Person SET password = %s WHERE username = %s'
		cursor.execute(query, (changepass, username))
		conn.commit()
		cursor.close()
	else:
		error = "Incorrect password"
		return render_template('changepass.html', error = error)
	return redirect(url_for('home'))

@app.route('/logout')
def logout():
	session.pop('username')
	return redirect('/')
		
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
