from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import time
import traceback, sys
import socket
import os

import mouse, keyboard

from launchMinecraft import launchMine, closeMine

import win32gui
import win32con

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done



class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.screenLocked = False
        self.timeSinceLastTeacherMsg = 0
        self.launchingMinecraft = False
        cred_path = os.path.join(os.path.dirname(sys.executable), 'credentials.txt')
        with open(cred_path) as f:
            self.PCname = f.readlines()[0]
        #self.PCname =
        #self.teachermsg = ''

        layout = QVBoxLayout()

        label = QLabel(self)
        keep_path = os.path.join(os.path.dirname(sys.executable), 'keep.png')
        pixmap = QPixmap(keep_path)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.showFullScreen() 
        
        w = QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)
        self.show()

        win32gui.SystemParametersInfo(win32con.SPI_SETFOREGROUNDLOCKTIMEOUT, 0, win32con.SPIF_SENDWININICHANGE | win32con.SPIF_UPDATEINIFILE)
        self.win32setHandle()
        win32gui.SetForegroundWindow(self.handle)

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.unlock_timer)
        self.timer.start()

        self.timer2 = QTimer()
        self.timer2.setInterval(20000)
        self.timer2.timeout.connect(self.broadcastIP_timer)
        self.timer2.start()

        tcpListener = Worker(self.listenTCP)
        tcpListener.signals.result.connect(self.do_what_teacher_said)
        tcpListener.signals.finished.connect(self.listen_again)
        self.threadpool.start(tcpListener)
        
        self.hide()

    def win32setHandle(self):
        win32gui.EnumWindows(self.win32enumHandler, None)
#
    def win32enumHandler(self, hwnd, lParam):
        if 'tchrHlprSt' in win32gui.GetWindowText(hwnd):
            self.handle = hwnd

    def progress_fn(self, n):
        print("%d%% done" % n)

    def execute_this_fn(self, progress_callback):
        for n in range(0, 5):
            time.sleep(1)
            progress_callback.emit(n*100/4)

        return "Done."

    def print_output(self, s):
        print(s)

    def thread_complete(self):
        print("THREAD COMPLETE!")

    def oh_no(self):
        # Pass the function to execute
        worker = Worker(self.execute_this_fn) # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.print_output)
        worker.signals.finished.connect(self.thread_complete)
        worker.signals.progress.connect(self.progress_fn)

        # Execute
        self.threadpool.start(worker)

    def unlock_timer(self):
        self.timeSinceLastTeacherMsg += 1
        if self.timeSinceLastTeacherMsg > 30:
            self.do_what_teacher_said('u')
            self.timeSinceLastTeacherMsg = 0

    def broadcastIP_timer(self):
        self.broadcastIP()


    def listenTCP(self, progress_callback):
        TCP_PORT = 5005
        BUFFER_SIZE = 20  # Normally 1024, but we want fast response

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', TCP_PORT)) #TCP_IPs
        s.listen(1)
        try: 
            conn, addr = s.accept()
        except:
            server.sendto(message, ('<broadcast>', 37020))
            return "Accept error"
        print ('Connection address:', addr)
        while 1:
            data = conn.recv(BUFFER_SIZE)
            if not data: 
                break
            print ("received data:", data.decode())
            teachermsg = data.decode()
            conn.send(data)  # echo                
        conn.close()
        return teachermsg

    def listen_again(self) :
        tcpListener = Worker(self.listenTCP)
        tcpListener.signals.result.connect(self.do_what_teacher_said)
        tcpListener.signals.finished.connect(self.listen_again)
        self.threadpool.start(tcpListener)

    def broadcastIP(self):
        MY_IP = socket.gethostbyname(socket.gethostname())
        #UDP_PORT = 5006
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        server.settimeout(1.5)
        server.bind(("", 44444))
        message = f"{self.PCname},{MY_IP}"
        server.sendto(message.encode(), ('<broadcast>', 37020))
        print(f"broadcasted msg {message}")

    def doNothing(self, e):
        print("keyboard hooked")
        keyboard.stash_state()

    def returnMouseBack(self, e):
        mouse.move(self.m_x, self.m_y, absolute = True)

    def launchPS(self, progress_callback):
        closeMine()
        result = launchMine("PS")
        return result

    def launchPR(self, progress_callback):
        closeMine()
        result = launchMine("PR")
        return result

    def minecraftLaunchReport(self, loginSuccessfull):
        if loginSuccessfull:
            print("Login was successfull")
        else:
            print("Login was UNsuccessfull")
        self.launchingMinecraft = False

    def do_what_teacher_said(self, msg):
        print("teacher said " + msg)
        self.timeSinceLastTeacherMsg = 0
        if msg == 'once':
            print('do it once')
        elif msg == 'l':
            if not self.screenLocked:
                self.show()
                win32gui.SetForegroundWindow(self.handle)
                keyboard.hook(self.doNothing, suppress=True)
                self.m_x, self.m_y = mouse.get_position()
                mouse.hook(self.returnMouseBack)
                self.screenLocked = True
        elif msg == 'u':
            if self.screenLocked:
                self.hide()
                keyboard.unhook_all()
                mouse.unhook_all()
                self.screenLocked = False
        elif msg == 'launchPS':
            if not(self.launchingMinecraft):
                minecraftLauncher = Worker(self.launchPS)
                minecraftLauncher.signals.result.connect(self.minecraftLaunchReport)
                self.threadpool.start(minecraftLauncher)
                self.launchingMinecraft = True
            else:
                print("Minecraft is already launching")

        elif msg == 'launchPR':
            if not(self.launchingMinecraft):
                minecraftLauncher = Worker(self.launchPR)
                minecraftLauncher.signals.result.connect(self.minecraftLaunchReport)
                self.threadpool.start(minecraftLauncher)
                self.launchingMinecraft = True
            else:
                print("Minecraft is already launching")
        elif msg == 'closeMine':
            if not(self.launchingMinecraft):
                closeMine()
            else:
                print("Minecraft is launching...")


app = QApplication([])
window = MainWindow()
app.exec_()
