import os.path
import random
import threading
import time
import json

import keyboard
import pygame.event
import tinytag
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSlider, QFileDialog
from pygame import mixer

from name_window import NameWindow
from scrolling_frame import ScrollingFrame
from song import Song
from song_item import SongItem

mixer.init(48000)
pygame.init()
mixer.music.set_endevent(pygame.USEREVENT + 1)


class MyMainWindow(QWidget):
    REPEAT_MODES = ['no', 'one']
    PLAY_MODES = ['play', 'pause']
    update = pyqtSignal()
    song_ended = pyqtSignal()
    show_name = pyqtSignal()
    name_window_closed = pyqtSignal()

    def __init__(self):
        super().__init__(None)

        self.setWindowTitle('Аудио-плеер')
        self.setWindowIcon(QIcon('images/window_icon.png'))

        self.update.connect(self.update_pos)
        self.song_ended.connect(self.on_song_ended)
        self.show_name.connect(self.on_show_name)
        self.name_window_closed.connect(self.on_name_window_closed)
        self.name_window = None
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.lblTitle = QLabel('Make My Day')
        self.lblTitle.setFont(QFont('Arial', 25, 2))
        self.vbox.addWidget(self.lblTitle)

        self.lblSinger = QLabel('Ace of Base')
        self.lblSinger.setFont(QFont('Arial', 15, 2))
        self.vbox.addWidget(self.lblSinger)

        self.hboxControls = QHBoxLayout()
        self.vbox.addLayout(self.hboxControls)

        # Controls:

        self.btn_repeater = QPushButton(QIcon('images/repeat_no.png'), '')
        self.btn_repeater.clicked.connect(self.btn_repeater_click)

        self.btn_prev = QPushButton(QIcon('images/previous.png'), '')
        self.btn_prev.clicked.connect(self.btn_prev_click)

        self.btn_play_pause = QPushButton(QIcon('images/play.png'), '')
        self.btn_play_pause.clicked.connect(self.btn_play_pause_click)

        self.btn_next = QPushButton(QIcon('images/next.png'), '')
        self.btn_next.clicked.connect(self.btn_next_click)

        self.btn_sorting = QPushButton(QIcon('images/sorting_A2Z.png'), '')
        self.btn_sorting.clicked.connect(self.btn_sorting_click)

        for i in [self.btn_repeater, self.btn_prev, self.btn_play_pause, self.btn_next, self.btn_sorting]:
            self.hboxControls.addWidget(i)
            i.setFixedHeight(75)
            i.setFixedWidth(75)
            i.setIconSize(QSize(60, 60))

        self.slider_out = QSlider(Qt.Horizontal)
        self.vbox.addWidget(self.slider_out)

        self.slider_in = QSlider(Qt.Horizontal)
        self.slider_in.valueChanged.connect(self.slider_move)

        self.vbox.addWidget(self.slider_in)

        self.hbox_time = QHBoxLayout()
        self.vbox.addLayout(self.hbox_time)

        self.lblTimeCurr = QLabel("0:00")
        self.hbox_time.addWidget(self.lblTimeCurr)

        self.hbox_time.addStretch(1)

        self.lblTimeEnd = QLabel("0:00")
        self.hbox_time.addWidget(self.lblTimeEnd)

        self.scroll_view = ScrollingFrame([])
        self.vbox.addWidget(self.scroll_view)

        self.hbox_playlist_controls = QHBoxLayout()
        self.vbox.addLayout(self.hbox_playlist_controls)

        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_song)
        self.hbox_playlist_controls.addWidget(self.btn_add)

        self.btn_del = QPushButton("Delete")
        self.btn_del.clicked.connect(self.delete_song)
        self.hbox_playlist_controls.addWidget(self.btn_del)

        self.btn_renew = QPushButton("Пересоздать")
        self.btn_renew.clicked.connect(self.renew_playlist)
        self.hbox_playlist_controls.addWidget(self.btn_renew)

        keyboard.on_press(lambda q: self.kb_handler(q))
        # keyboard.on_press_key('play/pause media', self.kb_handler)
        # Parameters

        self.position_moved = 0
        self.stopped = False

        if not os.path.exists('playlist.mplpl'):
            songs = QFileDialog.getOpenFileNames(
                self, "Выберите файлы",
                os.path.expanduser("~") + '/Music',
                "Music files (*.mp3);;All Files (*)"
            )[0]
            with open('playlist.mplpl', 'w') as f:
                f.write(json.dumps({
                    'repeat_mode': 'no',
                    'play_mode': 'pause',
                    'sorting_mode': 'A2Z',
                    'current_item': 0,
                    'current_pos': 0,
                    'songs': songs,
                }))

        with open('playlist.mplpl') as f:
            data = json.loads(f.read())
            self.repeat_mode = data['repeat_mode']
            self.play_mode = data['play_mode']
            self.sorting_mode = data['sorting_mode']
            self.current_item = data['current_item']

            self.songs = []

            for i in data['songs']:
                try:
                    tag = tinytag.TinyTag.get(i)
                except FileNotFoundError:
                    print('File not found')
                else:
                    song = Song(
                        tag.title,
                        i,
                        tag.artist,
                        tag.duration
                    )
                    song_item = SongItem(song)
                    song_item.add_click_listener(self.song_clicked)
                    self.songs.append(song_item)
            self.scroll_view.items = self.songs
            self.scroll_view.redraw_items()

            self.current = self.songs[self.current_item].song
            self.match_current()

            self.position_moved = data['current_pos']
            mixer.music.set_pos(data['current_pos'] // 1000)

        self.btn_play_pause.setIcon(QIcon(QPixmap(f'images/{"play" if self.play_mode == "pause" else "pause"}.png')))
        self.btn_repeater.setIcon(QIcon(QPixmap(f'images/repeat_{self.repeat_mode}.png')))
        self.btn_sorting.setIcon(QIcon(QPixmap(f'images/sorting_{self.sorting_mode}.png')))

        threading.Thread(target=self.song_check).start()
        threading.Thread(target=self.song_check_end).start()

    def add_song(self):
        dial = QFileDialog.getOpenFileNames(
            self, "Выберите файлы",
            os.path.expanduser("~") + '/Music',
            "Music files (*.mp3);;All Files (*)"
        )

        for filename in dial[0]:
            try:
                tag = tinytag.TinyTag.get(filename)
            except FileNotFoundError:
                print('File not found')
            else:
                song = Song(
                    tag.title,
                    filename,
                    tag.artist,
                    tag.duration
                )
                song_item = SongItem(song)
                song_item.add_click_listener(self.song_clicked)
                self.songs.append(song_item)
        self.scroll_view.redraw_items()
        self.save_data()

    def delete_song(self):
        idx = -1
        for i in range(len(self.songs)):
            if self.songs[i].song is self.current:
                idx = i
                break
        self.songs.pop(idx)
        if idx >= len(self.songs):
            idx = len(self.songs) - 1
        self.current = self.songs[idx]
        self.scroll_view.redraw_items()
        self.match_current()
        self.save_data()

    def renew_playlist(self):
        self.songs.clear()

        self.add_song()
        self.scroll_view.redraw_items()

        self.match_current()
        self.save_data()

    def get_current_position(self):
        return mixer.music.get_pos() + self.position_moved

    def on_show_name(self):
        if self.name_window is not None:
            self.name_window.stopped = True
            self.name_window.close()
        else:
            self.name_window = NameWindow(self.name_window_closed, self.current.formatted_name('::'))
            self.name_window.show()

    def on_name_window_closed(self):
        self.name_window = None

    def kb_handler(self, event: keyboard.KeyboardEvent):
        if event.name == 'play/pause media' and event.event_type == keyboard.KEY_DOWN:
            self.btn_play_pause_click()
        elif event.name == 'previous track' and event.event_type == keyboard.KEY_DOWN:
            self.btn_prev_click()
        elif event.name == 'next track' and event.event_type == keyboard.KEY_DOWN:
            self.btn_next_click()
        elif event.name == 'stop media' and event.event_type == keyboard.KEY_DOWN:
            self.show_name.emit()
        else:
            pass  # keyboard.play([event])

    def save_data(self):
        with open('playlist.mplpl', 'w') as f:
            f.write(json.dumps({
                'repeat_mode': self.repeat_mode,
                'play_mode': self.play_mode,
                'sorting_mode': self.sorting_mode,
                'current_item': ([i for i in range(len(self.songs)) if self.songs[i].song is self.current] or [0])[0],
                'current_pos': mixer.music.get_pos(),
                'songs': [i.song.filename for i in self.songs],
            }))

    def song_check(self):
        while not self.stopped:
            self.update.emit()
            self.save_data()
            time.sleep(0.05)

    def song_check_end(self):
        while not self.stopped:
            for _ in pygame.event.get():
                self.song_ended.emit()
            time.sleep(0.05)

    def on_song_ended(self):
        for i in self.songs:
            if i.song is self.current:
                if self.repeat_mode == 'no':
                    self.btn_next_click()
                else:
                    self.btn_next_click()
                    self.btn_prev_click()
                break

    def update_pos(self):
        self.slider_out.setValue(self.get_current_position())
        self.lblTimeCurr.setText(f'{self.get_current_position() // 1000 // 60}:{self.get_current_position() // 1000 % 60}')

    def btn_next_click(self):
        idx = -1

        for i in range(len(self.songs)):
            if self.songs[i].song is self.current:
                idx = i
                break

        next_ = idx + 1

        if next_ >= len(self.songs):
            next_ -= len(self.songs)
        self.current = self.songs[next_].song
        self.match_current()

    def btn_prev_click(self):
        idx = -1
        for i in range(len(self.songs)):
            if self.songs[i].song is self.current:
                idx = i
                break

        next_ = idx - 1
        if next_ < 0:
            next_ += len(self.songs)
        self.current = self.songs[next_].song
        self.match_current()

    def btn_repeater_click(self):
        if self.repeat_mode == 'no':
            self.repeat_mode = 'one'
        else:
            self.repeat_mode = 'no'
        self.btn_repeater.setIcon(QIcon(QPixmap(f'images/repeat_{self.repeat_mode}.png')))

    def btn_play_pause_click(self):
        if self.play_mode == 'play':
            self.play_mode = 'pause'
        else:
            self.play_mode = 'play'

        if self.play_mode == 'pause':
            mixer.music.pause()
        elif self.play_mode == 'play':
            mixer.music.unpause()

        self.btn_play_pause.setIcon(QIcon(QPixmap(f'images/{"play" if self.play_mode == "pause" else "pause"}.png')))

    def btn_sorting_click(self):
        if self.sorting_mode == 'A2Z':
            self.sorting_mode = 'Z2A'
        elif self.sorting_mode == 'Z2A':
            self.sorting_mode = 'shuffle'
        elif self.sorting_mode == 'shuffle':
            self.sorting_mode = 'A2Z'

        self.apply_sort()

        self.btn_sorting.setIcon(QIcon(QPixmap(f'images/sorting_{self.sorting_mode}.png')))

    def apply_sort(self):
        if self.sorting_mode == 'shuffle':
            random.shuffle(self.songs)
            self.scroll_view.items = self.songs
            self.scroll_view.redraw_items()
        elif self.sorting_mode == 'A2Z':
            self.songs.sort(key=lambda i: i.song.formatted_name())
            self.scroll_view.items = self.songs
            self.scroll_view.redraw_items()
        elif self.sorting_mode == 'Z2A':
            self.songs.sort(key=lambda i: i.song.formatted_name(), reverse=True)
            self.scroll_view.items = self.songs
            self.scroll_view.redraw_items()

    def match_current(self):
        for i in self.songs:
            if i.song is self.current:
                i.setStyleSheet('background-color: yellow;')
                self.lblSinger.setText(i.song.singer)
                self.lblTitle.setText(i.song.name)
                self.slider_in.setMaximum(round(i.song.duration * 1000))
                self.slider_out.setMaximum(round(i.song.duration * 1000))
                self.lblTimeEnd.setText(f'{int(i.song.duration // 60)}:{int(i.song.duration % 60)}')
                self.slider_in.setMinimum(0)
                self.slider_out.setMinimum(0)
                mixer.music.load(i.song.filename)

                mixer.music.play()
                self.position_moved = 0
                if self.play_mode == 'pause':
                    mixer.music.pause()
                if self.name_window is not None:
                    self.name_window.close()
                    self.name_window = None
                self.show_name.emit()
            else:
                i.setStyleSheet('')

    def closeEvent(self, event):
        self.save_data()
        self.stopped = True
        if self.name_window:
            self.name_window.close()
        event.accept()

    def song_clicked(self, song):
        self.current = song
        self.match_current()

    def slider_move(self, value):
        try:
            self.position_moved += value - self.get_current_position()
            mixer.music.set_pos((self.get_current_position()) // 1000)
        except pygame.error:
            print('Error')