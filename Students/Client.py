from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket
import threading
import sys
import traceback
import os

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
        self.label.grid(row=0, column=0, columnspan=4,
                        sticky=W+E+N+S, padx=5, pady=5)

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
        # os.remove(CACHE_FILE_NAME + str(self.sessionId) +
        #          CACHE_FILE_EXT)  # Delete the cache image of video

    def pauseMovie(self):
        """Pause button handler."""
        # TODO
        if self.state == self.PLAYING:
            self.requestSent(self.PAUSE)

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
                data, addr = self.rptSocket.recvfrom(20480)

                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    print("||Received Rtp Packet #" +
                          str(rtpPacket.seqNum()) + "|| ")

                    try:
                        if self.frameNbr + 1 != rtpPacket.seqNum():
                            self.counter += 1
                            print('!'*60 + "\nPACKET LOSS\n" + '!'*60)
                        currFrameNbr = rtpPacket.seqNum()
                        # version = rtpPacket.version()
                    except:
                        print("seqNum() error")
                        print('-'*60)
                        traceback.print_exc(file=sys.stdout)
                        print('-'*60)

                    if currFrameNbr > self.frameNbr:  # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(
                            rtpPacket.getPayload()))
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                print("Didn't receive data!")
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
        try:
            photo = ImageTk.PhotoImage(
                Image.open(imageFile))  # stuck here !!!!!!
        except:
            print("Photo error")
            print('-'*60)
            traceback.print_exc(file=sys.stdout)
            print('-'*60)

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
            # Update RTSP sequence number.
            # RTSP Sequence number starts at 1
            self.rtspSeq = 1
            # Write the RTSP request to be sent.
            # request = requestCode + movie file name + RTSP sequence number + Type of RTSP/Type of RTP + RTP port
            request = "SETUP" + self.fileName + "\n" + \
                str(self.rtspSeq) + "\n" + \
                " RTSP/1.0 RTP/UDP " + str(self.rtpPort)
            self.rtspSocket.send(request.encode())
            # Keep track of the sent request.
            # self.requestSent = SETUP
            self.requestSent = self.SETUP
        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number.
            # RTSP sequence number increments up by 1
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # Must inster the Session header and use the session ID returned in the SETUP response.
            # Must not put the transport header in this request
            # request = PLAY + RTSP sequence
            request = "PLAY" + "\n" + str(self.rtspSeq)
            self.rtspSocket.send(request.encode())
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
            request = "PAUSE" + "\n" + str(self.rtspSeq)
            self.rtspSocket.send(request.encode())
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
            request = "TEARDOWN" + "\n" + str(self.rtspSeq)
            self.rtspSocket.send(request.encode())
            # Keep track of the sent request.
            # self.requestSent = TEARDOWN
            self.requestSent = self.TEARDOWN
        else:
            return

        print("\nData sent:\n" + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        # TODO
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply)

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        # TODO
        print("Parsing Received Rtsp data...")
        lines = data.split('\n')
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
                        # Update RTSP state.
                        print("Updating RTSP state...")
                        # self.state = READY
                        self.state = self.READY
                        # Open RTP port
                        print("Setting Up RtpPort for Video Stream")
                        self.openRtpPort()

                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                        print('-'*60 + "\nClient is PLAYING...\n" + '-'*60)
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY

                        # The play thread exits. A new thread is created on resume
                        self.playEvent.set()

                    elif self.requestSent == self.TEARDOWN:
                        # self.state = TEARDOWN
                        # Flag the teardownAcked to close the socket
                        self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # -------------
        # TO COMPLETE
        # -------------
        # Create a new datagram socket to receive RTP packets from the server
        # self.rtpSocket = ...

        # Set the timeout value of the socket to 0.5sec
        # ...
        self.rtpSocket.settimeout(0.5)
# try:
        # Bind the socket to the address using the RTP port given by the client user
        # ...
# except:
# tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

        try:
            # Bind the socket to the address using the RTP port given by the client user
            # self.rtpSocket.connect(self.serverAddr,self.rtpPort)
            # WATCH OUT THE ADDRESS FORMAT!!!!!  rtpPort# should be bigger than 1024
            self.rtpSocket.bind((self.serverAddr, self.rtpPort))
            # self.rtpSocket.listen(5)
            print("Bind RtpPort Success")

        except:
            tkinter.messagebox.showwarning(
                'Connection Failed', 'Connection to rtpServer failed...')

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        # TODO
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:  # When the user presses cancel, resume playing.
            self.playMovie()
