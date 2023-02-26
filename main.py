import sys

from PyQt5.Qt import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWinExtras import QtWin

from mainWindow import MyMainWindow


app = QApplication(sys.argv)
app.setWindowIcon(QIcon('images/window_icon.png'))

QtWin.setCurrentProcessExplicitAppUserModelID('kgaklgjkasngflkansfldnkasffnl')

w = MyMainWindow()
w.show()

app.exec()
