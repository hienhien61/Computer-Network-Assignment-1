from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		
	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

	def setupMovie(self):
		"""Setup button handler."""
	#TODO
		self.teardownAcked = 0
		self.frameNbr = 0
		if (self.state == self.INIT):
			self.sendRtspRequest(self.SETUP)
	
	def exitClient(self):
		"""Teardown button handler."""
	#TODO
		self.sendRtspRequest(self.TEARDOWN)
		self.master.destroy()
		if self.requestSent != -1:
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)

	def pauseMovie(self):
		"""Pause button handler."""
	#TODO
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
	#TODO
		if self.state == self.READY:
			threading.Thread(target=self.listenRtp).start()
			self.check = threading.Event()
			self.check.clear()
			self.sendRtspRequest(self.PLAY)
	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		#TODO
		while True:
			try:
				datagram = self.rtpSocket.recv(32768)

				if datagram:
					data = RtpPacket()
					data.decode(datagram)
					seq_number_curr = data.seqNum()
					if seq_number_curr > self.frameNbr:
						self.frameNbr = seq_number_curr
						img_file = self.writeFrame(data.getPayload())
						self.updateMovie(img_file)

			except:
				# Pause listen when choose Pause button
				if self.check.is_set():
					break
				# Close socket when choose Teardown button
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
	#TODO
		img_name = CACHE_FILE_NAME+ str(self.sessionId) + CACHE_FILE_EXT
		with open(img_name,'wb') as file_object:
			file_object.write(data)
		return img_name
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
	#TODO
		img_object = Image.open(imageFile)
		img = ImageTk.PhotoImage(img_object)
		self.label.configure(image=  img, height=300)
		self.label.image = img
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
	#TODO
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr,self.serverPort))
		except:
			tkinter.messagebox.showwarning('Error',f"Connect to {self.serverAddr} fail")
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------
		
		if requestCode == self.SETUP and self.state == self.INIT:
			# Create thread to start receive RTSP reply from server, calling recvRtspReply function
			threading.Thread(target=self.recvRtspReply).start()
			# Update rtspSeq number
			self.rtspSeq += 1
			# Create request to send to server
			request = 'SETUP ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Transport: RTP/UDP; client_port= ' + str(self.rtpPort)

			# Update request to sent to server through requestSent attribute
			self.requestSent = self.SETUP

		elif requestCode == self.PLAY and self.state == self.READY:
			# Update rtspSeq number
			self.rtspSeq += 1

			# Create request to send to server
			request = 'PLAY ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Session: ' + str(self.sessionId)

			# Update request to sent to server through requestSent attribute
			self.requestSent = self.PLAY

		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			self.rtspSeq += 1

			request = 'PAUSE ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Session: ' + str(self.sessionId)

			self.requestSent = self.PAUSE

		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			self.rtspSeq += 1
			request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Session: ' + str(self.sessionId)

			self.requestSent = self.TEARDOWN

		elif requestCode == self.FORWARD and self.state == self.READY:
			self.rtspSeq += 1
			request = 'FORWARD ' + self.fileName + ' RTSP/1.0'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Session: ' + str(self.sessionId)
			self.requestSent = self.FORWARD

		elif requestCode == self.REWIND and self.state == self.READY:
			self.rtspSeq += 1
			request = 'REWIND ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Session: ' + str(self.sessionId)
			self.requestSent = self.REWIND
		else:
			return

		# Send the RTSP request using rtspSocket.
		# self.rtspSocket.send(request.)
		self.rtspSocket.send(request.encode('utf-8'))

		print('\nData sent:\n' + request)
	
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		#TODO
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply: 
				self.parseRtspReply(reply.decode("utf-8"))
			
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		#TODO
		lines = data.split('\n')

		if 'Description' in lines[1]:
			for line in lines:
				print(line)
			return

		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						self.state = self.READY
						# Open RTP port.
						self.openRtpPort()
					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING
					elif self.requestSent == self.PAUSE:
						self.state = self.READY
						# The play thread exits. A new thread is created on resume.
						self.check.set()
					elif self.requestSent == self.TEARDOWN:
						self.state = self.INIT
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Set the timeout value of the socket to 0.5sec
		# ...
		self.rtpSocket.settimeout(0.5)
		try:
			self.rtpSocket.bind(("", self.rtpPort))
		except:
			tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)
		

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		#TODO
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
