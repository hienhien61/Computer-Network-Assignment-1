from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket
import threading
import sys
import traceback
import os
import functools
import time

from RtpPacket import RtpPacket

import tkinter as tk

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

#Extend 1
#RTP Packet loss rate
rtp_loss = 0
rtp_sent = 0
#Calculate Play time
time_start = 0
time_end = 0
time_r = 0
#Calculate payload (data) sent
data_byte = 0


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
    LOAD = 9

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
        self.connectToServer()
        self.frameNbr = 0
        self.maxFrame = 0
        self.secPerFrame = 0
        self.totalFrame = 0
        self.speed = 20
        self.videos = []
        self.reset = False
        self.setupMovie()

    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI
    def createWidgets(self):
        """Build GUI."""

        # Create Description
        self.description = Text(self.master, width=80,
                                padx=3, pady=3, height=8)
        self.description.grid(row=3, columnspan=4, column=0)

        # Create Setup button
        # self.setup = Button(self.master, width=20, padx=3, pady=3)
        # self.setup["text"] = "Setup"
        # self.setup["command"] = self.setupMovie
        # self.setup.grid(row=1, column=0, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=0, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=1, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=2, padx=2, pady=2)

        # Create Describe button
        self.describe = Button(self.master, width=20, padx=3, pady=3)
        self.describe["text"] = "Describe"
        self.describe["command"] = self.describeMovie
        self.describe.grid(row=1, column=3, padx=2, pady=2)

        # Create Foward button
        self.forward = Button(self.master, width=20, padx=3, pady=3)
        self.forward["text"] = "Forward"
        self.forward["command"] = self.forwardMovie
        self.forward.grid(row=2, column=0, padx=2, pady=2)

        # Create Backward button
        self.backward = Button(self.master, width=20, padx=3, pady=3)
        self.backward["text"] = "Backward"
        self.backward["command"] = self.backwardMovie
        self.backward.grid(row=2, column=1, padx=2, pady=2)

        # Create Faster button
        self.faster = Button(self.master, width=20, padx=3, pady=3)
        self.faster["text"] = "Faster"
        self.faster["command"] = self.fasterMovie
        self.faster.grid(row=2, column=2, padx=2, pady=2)

        # Create Lower button
        self.lower = Button(self.master, width=20, padx=3, pady=3)
        self.lower["text"] = "Lower"
        self.lower["command"] = self.lowerMovie
        self.lower.grid(row=2, column=3, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4,
                        sticky=W+E+N+S, padx=5, pady=5)

        self.frameContainer = Frame(self.master, width=200)
        self.frameContainer.grid(column=4, row=2, rowspan=4)
        
        self.displays = []
        for i in range(2):
            DLabel = Label(self.master, height=1)
            DLabel.grid(row=1 + i, column=4, columnspan=4, sticky=W, padx=5, pady=5)
            self.displays.append(DLabel)

    def loadMovies(self):
        if self.state == self.READY or self.state == self.PLAYING:
            self.sendRtspRequest(self.LOAD)

    def setupMovie(self):
        """Setup button handler."""
        # TODO
        self.reset = True
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        # TODO
        #Ext 1: If video is playing, calculate time
        if self.state == self.PLAYING:
            global time_start, time_end, time_r
            time_end = time.time()
            time_r += time_end - time_start

        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # Close the gui window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) +
                  CACHE_FILE_EXT)  # Delete the cache image of video

    def pauseMovie(self):
        """Pause button handler."""
        # TODO
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)
            #Ext1: Calculate time
            global time_start, time_end, time_r
            time_end = time.time()
            time_r += time_end - time_start

    def playMovie(self):
        """Play button handler."""
        # TODO
        if self.reset == True:
            self.reset = False
            self.frameNbr = 0
        if self.state == self.READY:
            print("Playing Movie")
            # Create a new thread to connect to server and listen to the change on server
            threading.Thread(target=self.listenRtp).start()
            # Create a variable to save the next event after click on the button "Play"
            self.playEvent = threading.Event()

            # Block thread until the request PLAY send to server and client receive the response
            self.playEvent.clear()
            # Send request to server
            self.sendRtspRequest(self.PLAY)

            #Ext 1: Start calculate time
            global time_start
            time_start = time.time()

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
        # TODO
        while True:
            try:
                datagram = self.rtpSocket.recv(20480)

                if datagram:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(datagram)
                    currFrameNbr = rtpPacket.seqNum()
                    
                    #Ext 1: Set RTP sent count
                    global rtp_sent 
                    rtp_sent = currFrameNbr
                    if currFrameNbr > self.frameNbr:  # Discard the late packet
                        #Ext 1: Check and add RTP Packet loss
                        if (currFrameNbr - self.frameNbr) > 1:
                            global rtp_loss
                            rtp_loss = rtp_loss + (currFrameNbr - self.frameNbr)
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
                        
                    self.displays[0]["text"] = 'Current frame: ' + str(currFrameNbr)
                    self.displays[1]["text"] = 'Current view time: ' + str(int(currFrameNbr*0.05)) + ' / ' + str(int(self.maxFrame*0.05)) + ' (s)'

                    #Ext 1: Adding data bytes sent
                    global data_byte
                    data_byte += len(rtpPacket.getPayload())
            except:
                # if self.playEvent.is_set():
                #     break

                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    self.state = self.READY
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        # TODO
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT

        try:
            file = open(cachename, "wb")
        except:
            print("File open error")

        try:
            file.write(data)
        except:
            print("File write error")

        file.close()

        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        # TODO
        photo = ImageTk.PhotoImage(Image.open(imageFile))   # Stuck

        self.label.configure(image=photo, height=288)
        self.label.image = photo

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        # TODO
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkinter.messagebox.showwarning(
                'Connection Failed', 'Connection to \'%s\' failed.' % self.serverAddr)

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        print(str('\nState = ' + str(self.state)))
        # -------------
        # TO COMPLETE
        # -------------

        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number
            # RTSP Sequence number starts at 1
            self.rtspSeq = 1
            # Write the RTSP request to be sent
            # request = requestCode + movie file name + RTSP sequence number + Type of RTSP/RTP + RTP port
            request = 'SETUP ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Transport: RTP/UDP; client_port= ' + str(self.rtpPort)
            # Keep track of the sent request
            # self.requestSent = SETUP
            self.requestSent = self.SETUP
            self.state = self.READY

        elif requestCode == self.LOAD and (self.state == self.READY or self.state == self.PLAYING):
            # threading.Thread(target=self.recvRtspReply).start()

            self.rtspSeq = self.rtspSeq + 1

            request = 'LOAD ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + ' \n'
            request += 'Session: ' + str(self.sessionId)

            self.requestSent = self.LOAD
            self.state = self.READY

        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number
            # RTSP sequence number increments up by 1
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent
            # Inster the session ID returned in the SETUP response
            request = 'PLAY ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Session: ' + str(self.sessionId)
            # Keep track of the sent request.
            # self.requestSent = PLAY
            self.requestSent = self.PLAY
            self.state = self.PLAYING

        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            # Update RTSP sequence number.
            # RTSP sequence number increments up by 1
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = PAUSE + RTSP sequence
            request = 'PAUSE ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Session: ' + str(self.sessionId)
            # Keep track of the sent request.
            # self.requestSent = PAUSE
            self.requestSent = self.PAUSE
            self.state = self.READY

        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            # Update RTSP sequence number.
            # RTSP sequence number increments up by 1
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = TEARDOWN + RTSP sequence
            request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Session: ' + str(self.sessionId)
            # Keep track of the sent request.
            # self.requestSent = TEARDOWN
            self.requestSent = self.TEARDOWN
            self.state = self.INIT

        # Describe request
        elif requestCode == self.DESCRIBE and (self.state == self.PLAYING or self.state == self.READY):
            self.rtspSeq += 1

            request = 'DESCRIBE ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Session: ' + str(self.sessionId)

            self.requestSent = self.DESCRIBE

        # Forward request
        elif requestCode == self.FORWARD:
            self.rtspSeq += 1

            self.frameNbr += 50

            if self.frameNbr > self.maxFrame:
                self.frameNbr = self.maxFrame

            request = 'FORWARD ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Session: ' + str(self.sessionId) + '\n'
            request += 'Frame: ' + str(self.frameNbr)

            self.requestSent = self.FORWARD

        # Backward request
        elif requestCode == self.BACKWARD:
            self.rtspSeq += 1

            self.frameNbr -= 50

            if self.frameNbr < 0:
                self.frameNbr = 0

            request = 'BACKWARD ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Session: ' + str(self.sessionId) + '\n'
            request += 'Frame: ' + str(self.frameNbr)

            self.requestSent = self.BACKWARD

        # Faster request
        elif requestCode == self.FASTER:
            self.rtspSeq += 1
            self.speed *= 2

            request = 'FASTER ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Session: ' + str(self.sessionId)

            self.requestSent = self.FASTER

        # Lower request
        elif requestCode == self.LOWER:
            if self.speed / 2 >= self.MIN_SPEED:
                self.rtspSeq += 1
                self.speed /= 2

                request = 'LOWER ' + self.fileName + ' RTSP/1.0\n'
                request += 'CSeq: ' + str(self.rtspSeq) + '\n'
                request += 'Session: ' + str(self.sessionId)

                self.requestSent = self.LOWER

        else:
            return

        self.rtspSocket.send(request.encode('utf-8'))
        print("\nData sent:\n" + request)

        #Calculate statistics Extend 1
        if(requestCode == self.TEARDOWN):
            #Calculate RTP packet loss rate
            if rtp_sent > 0:
                rtp_loss_rate = rtp_loss/rtp_sent
            else: 
                rtp_loss_rate = 0.0
            print('RTP packet loss rate: ' + str(rtp_loss_rate))

            #Print time send request, data bytes and video data rate(bytes/second)
            print('Time: ' + str(round(time_r,2)))
            print('Data bytes: ' + str(data_byte))
            if time_r > 0:
                data_rate = round(data_byte/time_r,2)
            else:
                data_rate = 0
            print('Video data rate: ' + str(data_rate))

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        # TODO
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                # self.parseRtspReply(reply.decode('utf-8'))
                self.parseRtspReply(reply)

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        # TODO
        # print("Parsing Received Rtsp data...")
        lines = data.split(b'\n')
        if 'Description' in lines[1].decode('utf-8'):
            for line in lines:
                print(line)
            return
        seqNum = int(lines[1].split(b' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(b' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(b' ')[1]) == 200:

                    if self.requestSent == self.SETUP:
                        # -------------
                        # TO COMPLETE
                        # -------------
                        self.maxFrame = int(lines[3].decode().split(' ')[1])
                        self.secPerFrame = float(
                            lines[4].decode().split(' ')[1])
                        # Update RTSP state
                        self.state = self.READY
                        self.setList()
                        # Open RTP port
                        self.openRtpPort()

                    elif self.requestSent == self.LOAD:
                        self.state = self.READY

                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING

                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        # The play thread exits. A new thread is created on resume
                        self.playEvent.set()

                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket
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
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)

        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind(("", self.rtpPort))

        except:
            tkinter.messagebox.showwarning(
                'Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        # TODO
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:  # Pause video when pressing cancel
            self.playMovie()

    def setList(self):
        VIDEO_FOLDER = "./videos/"
        files = os.listdir(VIDEO_FOLDER)
        video_files = filter(lambda file: file.endswith(('.Mjpeg')), files)
        video_paths = {file: os.path.join(
            VIDEO_FOLDER, file) for file in video_files}

        self.videos = video_files

        def select_video(name):
            self.fileName = name[9:]
            # self.state = self.READY
            self.reset = True
            self.pauseMovie()
            self.loadMovies()
            self.description.insert(INSERT, "Switch to video " +
                                    self.fileName + '\n\n')

        for file, path in video_paths.items():
            # create a button and add it to the window
            button = Button(self.frameContainer, text=file, width=30,
                            padx=2, pady=2, command=lambda path=path: select_video(path))
            button.pack()
