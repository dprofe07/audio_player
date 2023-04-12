import time
from threading import Thread

from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QPen, QFontMetrics, QFont
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QHBoxLayout


class NameWindow(QWidget):
    redraw_signal = pyqtSignal()

    def __init__(self, signal, song, song_list, get_time_function, get_length_function):
        super().__init__()
        self.current_text = song.formatted_name('::')
        for i in range(len(song_list)):
            if song_list[i].song is song:
                if i == 0:
                    self.prev_text = 'R: ' + song_list[-1].song.formatted_name('::')
                else:
                    self.prev_text = song_list[i - 1].song.formatted_name('::')

                if i == len(song_list) - 1:
                    self.next_text = 'R: ' + song_list[0].song.formatted_name('::')
                else:
                    self.next_text = song_list[i + 1].song.formatted_name('::')

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        #self.setWindowOpacity(0.2)
        self.redraw_signal.connect(self.repaint)

        self.move(0, 0)
        self.setFixedWidth(QApplication.desktop().screenGeometry().width())
        self.setFixedHeight(QApplication.desktop().screenGeometry().height() // 6)


        self.font_current = self.get_good_font('Arial', self.current_text, 72)
        self.font_prev_next = self.get_good_font('Arial', max(self.next_text, self.prev_text, key=len), 20)
        self.get_length_function = get_length_function
        self.get_time_function = get_time_function
        self.stopped = False
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

        fm_current = QFontMetrics(self.font_current)

        fm_prev_next = QFontMetrics(self.font_prev_next)

        p.setFont(self.font_current)
        p.drawText(
            (self.width() - fm_current.width(self.current_text)) // 2, (self.height() - fm_current.height()) // 2, fm_current.width(self.current_text),
            fm_current.height(),
            0,
            self.current_text
        )

        p.setFont(self.font_prev_next)
        p.drawText(
            (self.width() - fm_prev_next.width(self.prev_text)) // 2, fm_prev_next.height() // 2,
            fm_prev_next.width(self.prev_text), fm_prev_next.height(),
            0,
            self.prev_text
        )

        p.drawText(
            (self.width() - fm_prev_next.width(self.next_text)) // 2, (self.height() - fm_prev_next.height()),
            fm_prev_next.width(self.next_text), fm_prev_next.height(),
            0,
            self.next_text
        )

        p.setOpacity(0.5)
        p.setBrush(QBrush(Qt.green))
        p.drawRect(
            0,
            int(self.height() * 0.9),
            int(self.width() * self.get_time_function() / self.get_length_function()),
            int(self.height() * 0.1)
        )

    def get_good_font(self, family, text, start_size):
        f = QFont(family, start_size)
        c = 1
        while self.width() - QFontMetrics(f).width(text) <= 20 or self.height() / 3 * 2 - QFontMetrics(f).height() <= 40:
            f = QFont(family, start_size - c)
            c += 1
        return f

    def checker(self):
        time.sleep(0.1)
        ts = time.time() + 5
        while not self.underMouse():
            if self.stopped:
                return
            if ts < time.time():
                break
            time.sleep(0.01)

            self.redraw_signal.emit()

        print('A')
        if not self.stopped and self.isVisible():
            print('B')
            self.close()
            print('C')

    def closeEvent(self, evt):
        self.stopped = True
        self.close_signal.emit()
        time.sleep(0.01)
        evt.accept()
