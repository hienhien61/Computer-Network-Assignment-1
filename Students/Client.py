from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket
import threading
import sys
import traceback
import os
import functools

from RtpPacket import RtpPacket

import tkinter as tk

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
        self.videos = []

    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI
    def createWidgets(self):
        """Build GUI."""

        # # Create Text
        # self.ann = Text(self.master, width=40, padx=3, pady=3, height=10)
        # self.ann.grid(row=4, columnspan=2)

        # Create Description
        self.des = Text(self.master, width=80, padx=3, pady=3, height=8)
        self.des.grid(row=2, columnspan=4, column=0)

        # for item in self.videos:
        #     button = Button(self.frameContainer, text=item, width=20,
        #                     padx=2, pady=2)
        #     button.pack(side=TOP)

        # for i in range(1, 6):
        #     self.video = Button(self.master, width=20, padx=3, pady=2)
        #     self.video["text"] = "movie"
        #     self.video.grid(row=i, column=4, padx=2, pady=2)

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
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4,
                        sticky=W+E+N+S, padx=5, pady=5)

        self.frameContainer = Frame(self.master, width=200)
        self.frameContainer.grid(column=4, row=1, rowspan=4)

        VIDEO_FOLDER = "./videos/"
        files = os.listdir(VIDEO_FOLDER)
        video_files = filter(lambda file: file.endswith(
            ('.mp4', '.avi', '.mkv', '.Mjpeg')), files)
        video_paths = {file: os.path.join(
            VIDEO_FOLDER, file) for file in video_files}

        def select_video(name):
            self.fileName = name
            self.des.insert(INSERT, "Switch to video " + name + '\n\n')

        for file, path in video_paths.items():
            # create a button and add it to the window
            button = Button(self.frameContainer, text=file, width=30,
                            padx=2, pady=2, command=lambda path=path: select_video(path))
            button.pack()

    def setupMovie(self):
        """Setup button handler."""
        # TODO
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        # TODO
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # Close the gui window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) +
                  CACHE_FILE_EXT)  # Delete the cache image of video

    def pauseMovie(self):
        """Pause button handler."""
        # TODO
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        # TODO
        if self.state == self.READY:
            print("Playing Movie")
            # Create a thread connecting to server
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()		# Save the next event
            self.playEvent.clear()		# Block the thread until server response
            self.sendRtspRequest(self.PLAY)

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

                    if currFrameNbr > self.frameNbr:  # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(
                            rtpPacket.getPayload()))

            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                # print("Didn't receive data!")
                if self.playEvent.is_set():
                    self.state = self.READY
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
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
        # -------------
        # TO COMPLETE
        # -------------
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number
            # RTSP Sequence number starts at 1
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent
            # request = requestCode + movie file name + RTSP sequence number + Type of RTSP/RTP + RTP port
            request = 'SETUP ' + self.fileName + ' RTSP/1.0\n'
            request += 'CSeq: ' + str(self.rtspSeq) + '\n'
            request += 'Transport: RTP/UDP; client_port= ' + str(self.rtpPort)
            # Keep track of the sent request
            # self.requestSent = SETUP
            self.requestSent = self.SETUP

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

        else:
            return

        self.rtspSocket.send(request.encode('utf-8'))
        print("\nData sent:\n" + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        # TODO
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply.decode('utf-8'))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        # TODO
        # print("Parsing Received Rtsp data...")
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
                        # -------------
                        # TO COMPLETE
                        # -------------
                        # Update RTSP state
                        self.state = self.READY
                        # Open RTP port
                        self.openRtpPort()

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
                'Connection Failed', 'Connection to rtpServer failed...')

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        # TODO
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:  # Pause video when pressing cancel
            self.pauseMovie()

    def setList(self):

        def func(name):
            self.fileName = name
            self.reset = True
            self.des.insert(INSERT, "Switch to file " + name + '\n\n')
        for item in self.videos:
            button = Button(self.frameContainer, text=item, width=20,
                            padx=2, pady=2, command=functools.partial(func, item))
            button.pack(side=TOP)
