import os
import urllib
import webapp2
import time
from google.appengine.api import images
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

class FileInfo(db.Model):
	blob = blobstore.BlobReferenceProperty(required=True)	
	uploaded_by = db.UserProperty(required=True)	
	userID = db.StringProperty()
	uploaded_at = db.DateTimeProperty(required=True, auto_now_add=True)
	filename = db.StringProperty()
	filetype = db.StringProperty()
	filesize = db.IntegerProperty()
 
class MainHandler(webapp2.RequestHandler):
  def get(self):
	
	user = users.get_current_user()
	
	validImages = ('image/bmp', 'image/jpeg', 'image/png', 
    'image/gif', 'image/tiff', 'image/x-icon')
	
	if user:
		user_files = FileInfo.all().filter('userID =', user.user_id())	
		user_files = user_files.fetch(1000)	
		
		html = template.render('templates/index.html', {'user':user, 'logout_url': users.create_logout_url('/')})

		for file in user_files:					
			if file.blob.content_type in validImages:
				image = images.get_serving_url(file.blob.key(), size=150, crop=False, secure_url=True)
			else:
				image = 'static/img/file.png'
			html = html + template.render('templates/file.html', {'file':file.blob, 'key':file.blob.key(), 'image':image})

		upload_url = blobstore.create_upload_url('/upload')
		html = html + template.render('templates/footer.html', {'upload_url' : upload_url})
		
		self.response.out.write(html)
	else:
		self.redirect(users.create_login_url(self.request.uri))


class Upload(blobstore_handlers.BlobstoreUploadHandler):
  def post(self):
	upload_files = self.get_uploads('file') 
	blob_info = upload_files[0]
	file_info = FileInfo(blob=blob_info.key(),filename=blob_info.filename,filetype=blob_info.content_type,filesize=blob_info.size,uploaded_by=users.get_current_user(),userID=users.get_current_user().user_id())
	db.put(file_info)
	time.sleep(3) # wait for 13s to allow for entry to be added so it displays on redirect
	self.redirect('/')

	
class Download(blobstore_handlers.BlobstoreDownloadHandler):
  def post(self):
	download_files = self.request.get_all('thisFile')
	for blob in download_files:		
		blob_url = str(urllib.unquote(blob))
		blob_info = blobstore.BlobInfo.get(blob_url)		
		self.send_blob(blob_info, save_as=blob_info.filename)

	
class Delete(webapp2.RequestHandler):
	def post(self):
		blob_key = self.request.get('thisFile')
		if not blob_key:
			self.redirect('/')
		else:
			blob_url = str(urllib.unquote(blob_key))
			blob_info = blobstore.BlobInfo.get(blob_url)
			user = users.get_current_user()
			user_files = FileInfo.all().filter('userID =', user.user_id())
			user_files = user_files.fetch(1000)	
			for file in user_files:
				if str(file.blob.key()) in blob_key:				
					db.delete(file)
					blobstore.delete(file.blob.key())
			time.sleep(3) # wait for 3s to allow for entry to be deleted on server
			self.redirect('/')

		
class About(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		html = template.render('templates/about.html', {'user':user, 'logout_url': users.create_logout_url('/')})	
		self.response.out.write(html)
		
app = webapp2.WSGIApplication([('/', MainHandler),
                               ('/upload', Upload),
							   ('/download',Download),
							   ('/delete', Delete),
							   ('/about', About),
							   ],
                              debug=False)

							  
'''

12: Set up the FileInfo datastore class using the db.Model class

#Main Handler

21: Define the main handler for the application homepage
24: Create a varuable user which is set by calling the get_current_user() method of users. This returns the user object of the currently logged in user
26: Set up a list of Valid image types to check blobs against later
29: If the get_current_user() method return a user and not a None value (i.e a user is logged in)
30: Get all the entries in the FileInfo datastore and apply a filter on it that checks the userID field of the entry against the id of the logged in user thus returning a query to get all the logged in users files.
31: call the .fetch() method on the query user_files. This returns the results of the filtered query as a list of FileInfo objects
33: Using template.render(), pass the method the template index.html and the dictionary of values to display on the page.
35: Iterate through the list stored in user_files
36: if the content_type attribute of the blob object in the entry matches any valid image types then set the image variable to be a thumbnail of said image
37: images.get_serving_url() Returns a URL that serves the image form the blobstore by passing the blob key and resizing it using the python PIL module
38: If the blob is not a valid image type then set the default file icon for display
40: Add more html to the html already rendered in line 33 and pass in the blob contained in the entry, the key of said blob and the image
42: Generate a blobstore upload url by calling blobstore.create_upload_url()
43: Finally render the footer.html and pass in the uplad url for use in the upload form

#Upload Handler

50: Define the upload handler with the BlobstoreUploadHandler to enable saving of blobs to the blobstore
51: As this mthod will be called when the page posts, define a post method.
52: Get the value of the form field 'file' that was posted and save the array in upload_files
53: Since multiple files would generate an error only get the first elemetn of the array
54: Set up the FilInfo object by  passing the contructor all of the required info for an object of that class
55: put() the FileInfo object to the datastore
56: sleep for 3s to allow for the datastore to update before refreshing the page
57: redirect to the main handler page to display the uploaded file.

#Download Handler

60: Define the Download handler with the BlobstoreDownloadHandler to enable downloading of files from the Blobstore.
61: Since this handler will again only be called when posting define a post method
62: get the value of 'thisFile' from the posted form values. the get_all method is used here to allow for the use of checkboxes
63: This will error is more than one checkbox is checked
64: get the string value of the "unescaped" value we stored in blob_key. This removes errors generated from escape characters in the string.
65: Save the BlobInfo of the file by passing the blob key to the BlobInfo.get() method which returns the blob
66: using self.send, provide the user with the save file prompt on their browser.

#Delte handler

69: Define the delete handler
70: Since this will again be called when the form posts, define a post method
71: Get the blob key value sent by the form as 'thisFile'
72: check there is a value sent
75: Get the unescaped string value of the key
76: store the blobInfo of the blob object by calling BlobInfo-get()
77: get the currently logged in user again
78: Query and fetch to get all of the users files in a list
80: Iterate through the list to find matching blob.key()s in the entries
82: If a match is found, remove it from the datastore AND the blobstore
84: Sleep to allow for the datastore to update
85: redurect to homepage to display files.

#About Hanlder

88: Set up a static page displaying some information about the project

#Set up app handlers

94: Define the applications handlers by stating which class handler to call when users hit each of the urls associated with them.
	Set debug to be false to prevent visibility of the code errors to users.

'''