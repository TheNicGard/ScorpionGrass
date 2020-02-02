#!/usr/bin/python

import AO3
import math
import os
import pickle
import random
import re
import sys
import urllib.parse
import wget
from PySide2 import QtCore, QtWidgets, QtGui
from urllib.parse import quote

def message(string):
    if textbox is not None:
        textbox.appendMessage(string + "\n")

def download_work(work, test_run):
    work_id = work[0]
    title = work[1]
    
    try:
        # apparently ao3 doesn't care what the file is called when requested?
        download_url = "https://archiveofourown.org/downloads/" + str(work_id) + "/bookmark.pdf" 
        message("Downloading \"" + title + "\" (" + str(work_id) + ") from:\n" + download_url)
        if not test_run:
            if not os.path.exists("works"):
                os.makedirs("works")
            # not sanitizing titles before saving them causes some downloads to fail
            title = re.sub('[' + re.escape(''.join(['?', '/', '\\', '<', '>', ':', '|', '*', '"'])) + ']', '', title)
            wget.download(download_url, os.path.join("works", title + ".pdf"))
    except Exception as e:
        message("[ERROR] Something bad happened while downloading!")
        message(str(e))

def get_session(username, password):
    return AO3.Session(username, password)

def saveSessionToCache(session, sessionFile):
    if session is not None:
        with open(sessionFile, "wb") as f:
            pickle.dump(session, f)
            message("Updated session cache-file %s." % sessionFile)
        f.close()
                
def loadSessionFromCache(sessionFile):
    session = None
    if os.path.getsize(sessionFile) > 0:
        with open(sessionFile, "rb") as f:
            session = pickle.load(f)
            message("Loaded session cache-file %s." % sessionFile)
        f.close()
    return session
    

class LogPane(QtWidgets.QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

    def appendMessage(self, string):
        print(string)
        self.append(string)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        super().update()
        
class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        super().setWindowTitle("ScorpionGrass")
        super().setWindowIcon(QtGui.QIcon("icon.png"))


        self.setLayout(QtWidgets.QVBoxLayout())
        
        global textbox
        textbox = LogPane()
        textbox.appendMessage("Hello World!")

        self.login_form = QtWidgets.QWidget()
        self.login_form_layout = QtWidgets.QFormLayout()
        self.login_button = QtWidgets.QPushButton("Log in")
        self.username_box = QtWidgets.QLineEdit()
        self.username_box.setPlaceholderText("Please enter username.")
        self.password_box = QtWidgets.QLineEdit()
        self.password_box.setPlaceholderText("Please enter password.")
        self.password_box.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.login_form_layout.addRow("Username", self.username_box)
        self.login_form_layout.addRow("Password", self.password_box)
        self.login_form_layout.addRow("", self.login_button)
        self.login_form.setLayout(self.login_form_layout)

        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setLineWidth(2)

        self.download_form = QtWidgets.QWidget()
        self.download_form_layout = QtWidgets.QFormLayout()
        self.download_form_layout.setLabelAlignment(QtCore.Qt.AlignRight)
        self.download_button = QtWidgets.QPushButton("Download Bookmarks!")
        self.bookmark_amount = QtWidgets.QSpinBox()
        self.test_run = QtWidgets.QCheckBox()
        self.current_user = QtWidgets.QLabel()
        self.logout_button = QtWidgets.QPushButton("Log out")
        self.download_form_layout.addRow("Number of bookmarks to download", self.bookmark_amount)
        self.download_form_layout.addRow("Test run", self.test_run)
        self.download_form_layout.addRow("", self.download_button)
        self.download_form_layout.addRow("", self.logout_button)
        self.download_form.setLayout(self.download_form_layout)

        self.layout().addWidget(textbox)
        self.layout().addWidget(self.login_form)
        self.layout().addWidget(self.line)
        self.layout().addWidget(self.download_form)
        
        self.login_button.clicked.connect(self.login_button_action)
        self.download_button.clicked.connect(self.download_button_action)
        self.logout_button.clicked.connect(self.logout_button_action)

        self.start()

    def start(self):
        self.session = None
        if os.path.isfile("session.pickle"):
            self.session = loadSessionFromCache("session.pickle")
        self.setLoggedInState(self.session is not None)

    def login_button_action(self):
        if len(self.username_box.text()) == 0 or len(self.password_box.text()) == 0:
            message("[ERROR] Please input a valid username and password!")
            return
        else:        
            message("Attempting to get session for " + self.username_box.text() + ".")
        
            while True:
                try:
                    self.session = get_session(self.username_box.text(), self.password_box.text())
                    saveSessionToCache(self.session, "session.pickle")
                    message("Get session for " + self.username_box.text() + "!")
                    self.setLoggedInState(True)
                    break
                except AO3.utils.LoginError:
                    message("[ERROR] Something failed while logging in!")
                    self.password_box.setText("")
                    return

    def download_button_action(self):
        do_download(self.session, self.bookmark_amount.value(), self.test_run.isChecked())

    def logout_button_action(self):
        self.setLoggedInState(False)
        if os.path.isfile("session.pickle"):
            os.remove("session.pickle")

    def setLoggedInState(self, state):
        if state:
            self.login_form.setEnabled(False)
            self.download_form.setEnabled(True)
            message(self.session.username + " has " + str(self.session.get_n_bookmarks()) + " bookmarks (note: the API currently does not read the number of bookmarks correctly).")
        else:
            self.login_form.setEnabled(True)
            self.download_form.setEnabled(False)
            
def do_download(session, number_to_download, test_run):
    # total_number_of_bookmarks = session.get_n_bookmarks()
    page_num = (number_to_download + 19) // 20

    for i in range(page_num):
        bookmarks = session.get_bookmarks(page=i + 1)

        if i + 1 < page_num or (i + 1 == page_num and number_to_download % 20 == 0):
            for k in range(20):
                download_work(bookmarks[k], test_run)
        else:
            for k in range(number_to_download % 20):
                download_work(bookmarks[k], test_run)

    message("Done downloading!")

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec_())
