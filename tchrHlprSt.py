from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import time
import traceback, sys
import socket

import mouse, keyboard

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
        self.counter = 0
        #self.teachermsg = ''

        layout = QVBoxLayout()
        #self.setMinimumSize(QSize(480, 80))
        #layout = QGridLayout()

        #self.l = QLabel("Start")
        label = QLabel(self)
        pixmap = QPixmap('keep.png')
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

        self.show()

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()


        tcpListener = Worker(self.listenTCP)
        tcpListener.signals.result.connect(self.do_what_teacher_said)
        tcpListener.signals.finished.connect(self.listen_again)
        #tcpListener.signals.progress.connect(self.)
        self.threadpool.start(tcpListener)

        self.hide()

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


    def recurring_timer(self):
        self.counter += 1
        if self.counter > 15:
            self.do_what_teacher_said('u')
        #self.l.setText("Counter: %d" % self.counter)

    def listenTCP(self, progress_callback):
        TCP_PORT = 5005
        BUFFER_SIZE = 20  # Normally 1024, but we want fast response

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #timeoutTime = 6
        #s.settimeout(timeoutTime)
        s.bind(('', TCP_PORT)) #TCP_IPs
        s.listen(1)
        try: 
            conn, addr = s.accept()
        except:
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

    def doNothing(self, e):
        print("keyboard hooked")
        keyboard.stash_state()

    def returnMouseBack(self, e):
        #if e is mouse.MoveEvent:
        #print("mouse moving")
        mouse.move(5000,5000)

    def do_what_teacher_said(self, msg):
        print("teacher said " + msg)
        self.counter = 0
        if msg == 'once':
            print('do it once')
        elif msg == 'l':
            if not self.screenLocked:
                self.show()
                #lmk.lockMandK()
                #lmk.lockKeyboard()
                #lmk.lockMouse()
                #ok = windll.user32.BlockInput(True) #enable block
                keyboard.hook(self.doNothing, suppress=True)
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
        #elif msg == 'timeout':
        #    timeoutTime = 6
        #    print("Didn't hear from server more then {} seconds.".format(timeoutTime))




app = QApplication([])
window = MainWindow()
app.exec_()
