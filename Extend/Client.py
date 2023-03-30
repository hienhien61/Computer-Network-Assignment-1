from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time

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
    DESCRIBE = 4
    FORWARD = 5
    BACKWARD = 6
    FASTER = 7
    LOWER = 8

    MIN_SPEED = 5
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
        self.maxFrame = 0
        self.secPerFrame = 0
        self.totalFrame = 0
        self.connectToServer()
        self.frameNbr = 0
        self.speed = 20

    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI
    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        # self.setup = Button(self.master, width=20, padx=3, pady=3)
        # self.setup["text"] = "Setup"
        # self.setup["command"] = self.setupMovie
        # self.setup.grid(row=1, column=0, padx=2, pady=2)

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
        self.teardown["text"] = "TearDown"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        #Create Describe button
        self.describe = Button(self.master, width=20, padx=3, pady=3)
        self.describe["text"] = "Describe"
        self.describe["command"] = self.describeMovie
        self.describe.grid(row=1, column=4, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5)

        # Create Description
        self.description = Text(self.master, width=40, padx=3, pady=3, height=10)
        self.description.grid(row=4, columnspan=2, column=2)

        # Create Foward button
        self.forward = Button(self.master, width=20, padx=3, pady=3)
        self.forward["text"] = "Forward"
        self.forward["command"] = self.forwardMovie
        self.forward.grid(row=1, column=5, padx=2, pady=2)

        # Create Backward button
        self.backward = Button(self.master, width=20, padx=3, pady=3)
        self.backward["text"] = "Backward"
        self.backward["command"] = self.backwardMovie
        self.backward.grid(row=1, column=6, padx=2, pady=2)

        # Create Faster button
        self.faster = Button(self.master, width=20, padx=3, pady=3)
        self.faster["text"] = "Faster"
        self.faster["command"] = self.fasterMovie
        self.faster.grid(row=1, column=7, padx=2, pady=2)

        # Create Lower button
        self.lower = Button(self.master, width=20, padx=3, pady=3)
        self.lower["text"] = "Lower"
        self.lower["command"] = self.lowerMovie
        self.lower.grid(row=2, column=2, padx=2, pady=2)

    def setupMovie(self):
        """Setup button handler."""
        self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # Close the gui window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)  # Delete the cache image from video

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)
            time.sleep(0.1)
            
        if self.state == self.READY:
            # Create a new thread to connect to server and listen to the change on server
            threading.Thread(target=self.listenRtp).start()
            # Create a variable to save the next event after click on the button "Play"
            self.playEvent = threading.Event()

            # Block thread until the request PLAY send to server and client receive the response
            self.playEvent.clear()
            # Send request to server
            self.sendRtspRequest(self.PLAY)

    def describeMovie(self):
        """Describe button handler."""
        self.sendRtspRequest(self.DESCRIBE)

    def forwardMovie(self):
        """Forward button handler."""
        self.sendRtspRequest(self.FORWARD)

    def backwardMovie(self):
        """Backward button handler."""
        self.sendRtspRequest(self.BACKWARD)

    def fasterMovie(self):
        """Faster button handler."""
        self.sendRtspRequest(self.FASTER)

    def lowerMovie(self):
        """Lower button handler."""
        self.sendRtspRequest(self.LOWER)

    def listenRtp(self):
        """Listen for RTP packets."""
        while True:
            try:
                data, addr = self.rtpSocket.recvfrom(20480)  # load all bytes need to display
                if data:
                    rptData = RtpPacket()
                    rptData.decode(data)

                    seqNum = rptData.seqNum()

                    if seqNum > self.frameNbr:  # Discard the late packet
                        self.frameNbr = seqNum
                        self.updateMovie(
                            self.writeFrame(rptData.getPayload())
                        )  # send cache name to update movie to change content

            except:
                if self.playEvent.is_set():
                    break

                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT  # name of cache file
        file = open(cachename, "wb")  # open file with authorization: write and the standard file is binary
        file.write(data)
        file.close()

        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        photo = ImageTk.PhotoImage(
            Image.open(imageFile)
        )  # read the data and transger to variable "photo" by using Tk package

        self.label.configure(image=photo, height=288)
        self.label.image = photo  # update screen

    def connectToServer(self):
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' % self.serverAddr)

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        # -------------
        # TO COMPLETE
        # -------------
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()

            self.rtspSeq = 1
            # save the content of action
            msg = 'SETUP ' + self.fileName + ' RTSP/1.0\n' \
                    'CSeq: ' + str(self.rtspSeq) + '\n' \
                    'Transport: RTP/UDP; client_port= ' + str(self.rtpPort)
            self.requestSent = self.SETUP
        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            self.rtspSeq += 1

            msg = 'PLAY ' + self.fileName + ' RTSP/1.0\n' \
                    'CSeq: ' + str(self.rtspSeq) + '\n' \
                    'Session: ' + str(self.sessionId)
            self.requestSent = self.PLAY
        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            self.rtspSeq += 1

            msg = 'PAUSE ' + self.fileName + ' RTSP/1.0\n' \
                    'CSeq: ' + str(self.rtspSeq) + '\n' \
                    'Session: ' + str(self.sessionId)
            self.requestSent = self.PAUSE
        # Teardown request
        elif requestCode == self.TEARDOWN and self.state != self.INIT:
            self.rtspSeq += 1

            msg = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\n' \
                    'CSeq: ' + str(self.rtspSeq) + '\n' \
                    'Session: ' + str(self.sessionId)
            self.requestSent = self.TEARDOWN
        # Describe request
        elif requestCode == self.DESCRIBE and (self.state == self.PLAYING or self.state == self.READY):
            self.rtspSeq += 1

            msg = 'DESCRIBE ' + self.fileName + ' RTSP/1.0\n' \
                    'CSeq: ' + str(self.rtspSeq) + '\n' \
                    'Session: ' + str(self.sessionId)
            self.requestSent = self.DESCRIBE
        # Forward request
        elif requestCode == self.FORWARD:
            self.rtspSeq += 1

            self.frameNbr += 50

            if self.frameNbr > self.maxFrame:
                self.frameNbr = self.maxFrame

            msg = 'FORWARD ' + self.fileName + ' RTSP/1.0\n' \
                    'CSeq: ' + str(self.rtspSeq) + '\n' \
                    'Session: ' + str(self.sessionId) +'\n' \
                    'Frame: ' + str(self.frameNbr)
            self.requestSent = self.FORWARD
        # Backward request
        elif requestCode == self.BACKWARD:
            self.rtspSeq += 1

            self.frameNbr -= 50

            if self.frameNbr < 0:
                self.frameNbr = 0

            msg = 'BACKWARD ' + self.fileName + ' RTSP/1.0\n' \
                    'CSeq: ' + str(self.rtspSeq) + '\n' \
                    'Session: ' + str(self.sessionId) + '\n' \
                    'Frame: ' + str(self.frameNbr)
            self.requestSent = self.BACKWARD
        # Faster request
        elif requestCode == self.FASTER:
            self.rtspSeq += 1
            self.speed *= 2

            msg = 'FASTER ' + self.fileName + ' RTSP/1.0\n' \
                    'CSeq: ' + str(self.rtspSeq) + '\n' \
                    'Session: ' + str(self.sessionId)
            self.requestSent = self.FASTER
        # Lower request
        elif requestCode == self.LOWER:
            if self.speed/2 >= self.MIN_SPEED:

                self.rtspSeq += 1
                self.speed /= 2

                msg = 'LOWER ' + self.fileName + ' RTSP/1.0\n' \
                        'CSeq: ' + str(self.rtspSeq) + '\n' \
                        'Session: ' + str(self.sessionId)
                self.requestSent = self.LOWER

        else:
            return

        # Send request to server using rtspSocket
        self.rtspSocket.sendall(bytes(msg, 'utf8'))

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            data = self.rtspSocket.recv(1024)  # each request will be received 1024 bytes

            if data:
                self.parseRtspReply(data)
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        lines = data.split(b'\n')
        seqNum = int(lines[1].split(b' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(b' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(b' ')[1]) == 200:  # The status code 200 is OK
                    if self.requestSent == self.SETUP:

                        self.maxFrame = int(lines[3].decode().split(' ')[1])
                        self.secPerFrame = float(lines[4].decode().split(' ')[1])
                        # Update state.
                        self.state = self.READY
                        # Open RTP port.
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1
                    elif self.requestSent == self.DESCRIBE:
                        temp = lines[3].decode()
                        for i in range(4, len(lines)):
                            temp += '\n' + lines[i].decode()
                        self.description.insert(INSERT, temp + '\n\n')

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # -------------
        # TO COMPLETE
        # -------------
        # Create a new datagram socket to receive RTP packets from the server
        # self.rtpSocket = ...

        # Set the timeout value of the socket to 0.5sec
        # ...
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)

        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind(("", self.rtpPort))
        except:
            tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)  # Delete the cache image from video
            self.exitClient()
        else:  # When the user presses cancel, resume playing.
            self.playMovie()