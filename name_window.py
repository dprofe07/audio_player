import time
from threading import Thread

from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QPen, QFontMetrics, QFont
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QHBoxLayout


class NameWindow(QWidget):
    def __init__(self, signal, text):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        #self.setWindowOpacity(0.2)

        self.move(0, 0)
        self.setFixedWidth(QApplication.desktop().screenGeometry().width())
        self.setFixedHeight(QApplication.desktop().screenGeometry().height() // 10)

        self.stopped = False
        self.text = text
        self.close_signal = signal

        Thread(target=self.checker).start()

    def paintEvent(self, evt):
        canvas = QPixmap(self.rect().size())

        canvas.fill(Qt.transparent)  # fill transparent (makes alpha channel available)

        p = QPainter(self)  # draw on the canvas

        p.setBrush(QBrush(Qt.black))  # use the color you like
        p.setPen(QPen(Qt.transparent))
        p.setOpacity(0.2)
        p.drawRect(0, 0, self.width(), self.height())
        p.setPen(Qt.white)
        p.setOpacity(1)

        font = self.get_good_font('Arial', 72)
        fm = QFontMetrics(font)

        p.setFont(font)
        p.drawText((self.width() - fm.width(self.text)) // 2, (self.height() - fm.height()) // 2, fm.width(self.text), fm.height(), 0, self.text)

    def get_good_font(self, family, start_size):
        f = QFont(family, start_size)
        c = 1
        while self.width() - QFontMetrics(f).width(self.text) <= 20 or self.height() - QFontMetrics(f).height() <= 40:
            f = QFont(family, start_size - c)
            c += 1
        return f

    def checker(self):
        ts = time.time() + 5
        while (not self.underMouse()):
            if self.stopped:
                return
            if ts < time.time():
                break
            time.sleep(0.001)
        if not self.stopped:
            self.close()

    def closeEvent(self, evt):
        self.close_signal.emit()
        self.stopped = True
        time.sleep(0.01)
        evt.accept()
