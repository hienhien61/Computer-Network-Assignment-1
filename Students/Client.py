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
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        # Create a label to display the movie

        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5)

    #####################################################################
    def setupMovie(self):
        """Setup button handler."""
        # TODO: sent Rtsp request to server
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        # TODO: sent Rtsp request to server, close the GUI window, delete cache image
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # Close the gui window

        # Delete the cache image from video only if there had been a request sent
        if self.requestSent != -1:
            os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)

    def pauseMovie(self):
        """Pause button handler."""
        # TODO sent Rtsp request
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY:
            # print("Play movie")
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

    #######################################################################

    def listenRtp(self):
        """Listen for RTP packets."""
        # TODO continously receive data from rtpSocket, use RtpPacket from RtpPacket.py
        # TODO take frame number from rtpPacket and update the image with updateMovie and writeFrame
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    currFrameNbr = rtpPacket.seqNum()
                    print("Current Seq Num: " + str(currFrameNbr))

                    if currFrameNbr > self.frameNbr:  # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        # TODO create a temp image file (USE CACHE_FILE_NAME, CACHE_FILE_EXIT), write data to that temp file, return the file
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()

        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        # TODO  update the self.label (SEARCH how to insert label with image)
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image=photo, height=288)
        self.label.image = photo

    ###################################################################
    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        # create a socket to connect to server
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
            request = 'PAUSE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionId)
            self.requestSent = self.PAUSE

        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            self.rtspSeq += 1
            request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionId)
            self.requestSent = self.TEARDOWN
        else:
            return

        self.rtspSocket.send(request.encode('utf-8'))
        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        # TODO while TRUE loop to continously listening for reply. if recveived then parse
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
        # TODO analyze reply from server, when needed call openRtpPort to recevie Rtp file
        datas = data.split('\n')
        # get Sequence number from server Rtsp reply
        seqNum = int(datas[1].split(' ')[1])

        if seqNum == self.rtspSeq:
            session = int(datas[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID match
            if self.sessionId == session:
                if int(datas[0].split(' ')[1]) == 200:
                    # Check request and current STATE
                    if self.requestSent == self.SETUP:
                        self.state = self.READY
                        # print(self.state)
                        # open RTP port to listen for file
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                        # print(self.state)
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        # print(self.state)
                        self.playEvent.set()
                    # create new threat
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        # print(self.state)
                        # Acked flag changed to true (=1)
                        self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)
        try:
            self.rtpSocket.bind(("", self.rtpPort))
        except:
            tkinter.messagebox.showwarning('Bind RTP port unsuccessful', 'Unable to bind PORT=%d' % self.rtpPort)

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        # TODO
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
