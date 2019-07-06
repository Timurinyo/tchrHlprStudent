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
#import win32process

#from pywinauto.findwindows    import find_window
#from pywinauto.win32functions import SetForegroundWindow

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
        #self.setMinimumSize(QSize(480, 80))
        #layout = QGridLayout()

        #self.l = QLabel("Start")
        label = QLabel(self)
        keep_path = os.path.join(os.path.dirname(sys.executable), 'keep.png')
        pixmap = QPixmap(keep_path)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.showFullScreen() 


        #b = QPushButton("DANGER!")
        #b.pressed.connect(self.oh_no)

        #layout.addWidget(self.l)
        #layout.addWidget(b)

        w = QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)
        #self.raise_()
        #self.activateWindow()
        self.show()

        #self.win32bringToFront()
        win32gui.SystemParametersInfo(win32con.SPI_SETFOREGROUNDLOCKTIMEOUT, 0, win32con.SPIF_SENDWININICHANGE | win32con.SPIF_UPDATEINIFILE)
        self.win32setHandle()
        win32gui.SetForegroundWindow(self.handle)
        #self.SetFocus()
        #win32gui.EnumWindows(self.win32enumHandler, None)

        #self.hwnd = win32gui.FindWindow('', '')

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        #self.timer_Sec = QTimer()
        #self.timer_Sec.setInterval(1000)
        #self.timer_Sec.timeout.connect(self.increase_time)
        #self.timer_Sec.start()

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
        #tcpListener.signals.progress.connect(self.)
        self.threadpool.start(tcpListener)

        #IPbroadcaster = Worker(self.broadcastIP)
        #IPbroadcaster.signals.result.connect(self.)

        self.hide()


    def win32setHandle(self):
        win32gui.EnumWindows(self.win32enumHandler, None)
#
    def win32enumHandler(self, hwnd, lParam):
        if 'tchrHlprSt' in win32gui.GetWindowText(hwnd):
            self.handle = hwnd
    #        self.SetFocus()
    #        #win32gui.SetForegroundWindow(hwnd)

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

    #def increase_time(self):
    #    self.timeSinceLastTeacherMsg += 1

    def unlock_timer(self):
        self.timeSinceLastTeacherMsg += 1
        if self.timeSinceLastTeacherMsg > 30:
            self.do_what_teacher_said('u')
            self.timeSinceLastTeacherMsg = 0
            #if self.timeSinceLastTeacherMsg
            #self.timeSinceLastTeacherMsg = 0
        #if self.timeSinceLastTeacherMsg > 5:
        #self.l.setText("timeSinceLastTeacherMsg: %d" % self.timeSinceLastTeacherMsg)

    def broadcastIP_timer(self):
        self.broadcastIP()


    def listenTCP(self, progress_callback):
        TCP_PORT = 5005
        BUFFER_SIZE = 20  # Normally 1024, but we want fast response

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #timeoutTime = 2
        #s.settimeout(timeoutTime)
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
        #tcpListener.signals.progress.connect(self.)
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
        #if e is mouse.MoveEvent:
        #print("mouse moving")
        mouse.move(self.m_x, self.m_y, absolute = True)

    def launchPS(self, progress_callback):
        closeMine()
        result = launchMine("PS")
        return result
            #self.launchingMinecraft = True
            #result = launchMine("PS")
            #return result

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
#
    #def minecraftReport2(self):
    #    print("minecraft test finished")

    def do_what_teacher_said(self, msg):
        print("teacher said " + msg)
        self.timeSinceLastTeacherMsg = 0
        if msg == 'once':
            print('do it once')
        elif msg == 'l':
            if not self.screenLocked:
                #self.raise_()
                #self.activateWindow()
                self.show()
                win32gui.SetForegroundWindow(self.handle)
                #self.SetFocus()
                #lmk.lockMandK()
                #lmk.lockKeyboard()
                #lmk.lockMouse()
                #ok = windll.user32.BlockInput(True) #enable block
                keyboard.hook(self.doNothing, suppress=True)
                self.m_x, self.m_y = mouse.get_position()
                mouse.hook(self.returnMouseBack)
                self.screenLocked = True
        elif msg == 'u':
            if self.screenLocked:
                #ws.unlockScreen()
                self.hide()
                #self.unlockMouse()
                keyboard.unhook_all()
                mouse.unhook_all()
                #lmk.unlockMandK()
                #ok = windll.user32.BlockInput(False) #disable block
                self.screenLocked = False
        elif msg == 'launchPS':
            if not(self.launchingMinecraft):
                minecraftLauncher = Worker(self.launchPS)
                minecraftLauncher.signals.result.connect(self.minecraftLaunchReport)
                #minecraftLauncher.signals.finished.connect(self.minecraftReport2)
                #minecraftLauncher.signals.progress.connect(self.)
                self.threadpool.start(minecraftLauncher)
                self.launchingMinecraft = True
            else:
                print("Minecraft is already launching")

            #launchMine("PS")
        elif msg == 'launchPR':
            if not(self.launchingMinecraft):
                minecraftLauncher = Worker(self.launchPR)
                minecraftLauncher.signals.result.connect(self.minecraftLaunchReport)
                #minecraftLauncher.signals.result.connect(self.minecraftReport1)
                #minecraftLauncher.signals.finished.connect(self.minecraftReport2)
                self.threadpool.start(minecraftLauncher)
                self.launchingMinecraft = True
            else:
                print("Minecraft is already launching")
            #launchMine("PR")
        elif msg == 'closeMine':
            if not(self.launchingMinecraft):
                closeMine()
            else:
                print("Minecraft is launching. Wait for it to be launched")

    #from https://github.com/dictation-toolbox/dragonfly/issues/86 and https://github.com/pywinauto/pywinauto/issues/117
    #def SetFocus(self):
#
    #    """
    #    Set the focus to this control.
    #    Bring the window to the foreground first if necessary.
    #    """
#
    #    # find the current foreground window
    #    cur_foreground = win32gui.GetForegroundWindow()
#
    #    # if it is already foreground then just return
    #    if self.handle != cur_foreground:
    #        # set the foreground window
#
    #        # get the thread of the window that is in the foreground
    #        cur_fore_thread = win32process.GetWindowThreadProcessId(
    #            cur_foreground)[0]
#
    #        # get the thread of the window that we want to be in the foreground
    #        control_thread = win32process.GetWindowThreadProcessId(
    #            self.handle)[0]
#
    #        # if a different thread owns the active window
    #        if cur_fore_thread != control_thread:
    #            # Attach the two threads and set the foreground window
    #            try:
    #                win32process.AttachThreadInput(control_thread, cur_fore_thread, False)
    #            except:
    #                print("AttachThreadInput exception")
    #                #print(control_thread)
    #                #print(cur_fore_thread)
    #                #input("Exit?")
    #            #self.actions.log('Call SetForegroundWindow within attached '
    #            #                 'threads - {0} & {1}.'.format(control_thread,
    #            #                                               cur_fore_thread,
    #            #                                               ))
    #            win32gui.SetForegroundWindow(self.handle)
#
    #            # ensure foreground window has changed to the target
    #            # or is 0(no foreground window) before the threads detaching
#
    #            while (win32gui.GetForegroundWindow() in [self.TopLevelParent().handle, 0]):
    #                pass
#
    #            # get the threads again to check they are still valid.
    #            cur_fore_thread = win32process.GetWindowThreadProcessId(
    #                cur_foreground)[0]
    #            control_thread = win32process.GetWindowThreadProcessId(
    #                self.handle)[0]
#
    #            if cur_fore_thread and control_thread:  # both are valid
    #                # Detach the threads
    #                win32process.AttachThreadInput(control_thread,
    #                                               cur_fore_thread,
    #                                               0)
    #        else:
    #            # same threads - just set the foreground window
    #            #self.actions.log('Call SetForegroundWindow within one thread.')
    #            win32gui.SetForegroundWindow(self.handle)
#
    #        # make sure that we are idle before returning
    #        #win32functions.WaitGuiThreadIdle(self)
#
    #        # only sleep if we had to change something!
    #        #time.sleep(Timings.after_setfocus_wait)
    #        #closeMine()
#
#
    #    #elif msg == 'timeout':
    #    #    timeoutTime = 6
    #    #    print("Didn't hear from server more then {} seconds.".format(timeoutTime))


app = QApplication([])
window = MainWindow()
app.exec_()
