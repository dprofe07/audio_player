from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout


class SongItem(QWidget):
    def __init__(self, song, parent=None):
        super().__init__(parent)

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.lbl_title = QLabel(song.formatted_name())
        self.vbox.addWidget(self.lbl_title)

        self.song = song

    def add_click_listener(self, listener):
        self.mousePressEvent = lambda i: listener(self.song)