import functools
import json
import os.path
import random
import threading
import time

import keyboard
import pygame.event
import tinytag
from PyQt5.QtCore import QSize, Qt, pyqtSignal
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


def no_error(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            print(f'NE: {e.__class__.__name__}: {e.args}')
    return wrapper


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

        self.lblTitle = QLabel('Title')
        self.lblTitle.setFont(QFont('Arial', 25, 2))
        self.vbox.addWidget(self.lblTitle)

        self.lblSinger = QLabel('Singer')
        self.lblSinger.setFont(QFont('Arial', 15, 2))
        self.vbox.addWidget(self.lblSinger)

        self.hboxControls = QHBoxLayout()
        self.vbox.addLayout(self.hboxControls)

        # Controls:

        self.btn_repeater = QPushButton(QIcon('images/repeat_no.png'), '')
        self.btn_repeater.clicked.connect(lambda e: self.btn_repeater_click())

        self.btn_prev = QPushButton(QIcon('images/previous.png'), '')
        self.btn_prev.clicked.connect(lambda e: self.btn_prev_click())

        self.btn_play_pause = QPushButton(QIcon('images/play.png'), '')
        self.btn_play_pause.clicked.connect(lambda e: self.btn_play_pause_click())

        self.btn_next = QPushButton(QIcon('images/next.png'), '')
        self.btn_next.clicked.connect(lambda e: self.btn_next_click())

        self.btn_sorting = QPushButton(QIcon('images/sorting_A2Z.png'), '')
        self.btn_sorting.clicked.connect(lambda e: self.btn_sorting_click())

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
        self.btn_add.clicked.connect(lambda e: self.add_song())
        self.hbox_playlist_controls.addWidget(self.btn_add)

        self.btn_del = QPushButton("Delete")
        self.btn_del.clicked.connect(lambda e: self.delete_song())
        self.hbox_playlist_controls.addWidget(self.btn_del)

        self.btn_renew = QPushButton("Пересоздать")
        self.btn_renew.clicked.connect(lambda e: self.renew_playlist())
        self.hbox_playlist_controls.addWidget(self.btn_renew)

        keyboard.hook(lambda q: self.kb_handler(q))
        #keyboard.on_release(lambda q: [print(q), self.kb_handler(q)])
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

            self.current_idx = self.current_item
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
        self.songs.pop(self.current_idx)
        if self.current_idx >= len(self.songs):
            self.current_idx = len(self.songs) - 1
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
        if self.name_window is not None and not self.name_window.stopped:
            self.name_window.stopped = True
            if self.name_window.isVisible():
                self.name_window.close()
        elif True:
            self.name_window = NameWindow(
                self.name_window_closed, self.current_idx, # self.current.formatted_name('::'),
                self.songs,
                lambda: self.get_current_position() / 1000, lambda: self.current.duration
            )
            self.name_window.show()

    def on_name_window_closed(self):
        self.name_window = None

    def kb_handler(self, event: keyboard.KeyboardEvent):
        if event.name == 'play/pause media' and event.event_type == keyboard.KEY_DOWN:
            self.btn_play_pause_click()
        elif event.name == 'previous track' and event.event_type == keyboard.KEY_DOWN:
            if keyboard.is_pressed('shift'):
                self.position_moved -= 5000
                mixer.music.set_pos(self.get_current_position() // 1000)
            else:
                self.btn_prev_click()
        elif event.name == 'next track' and event.event_type == keyboard.KEY_DOWN:
            if keyboard.is_pressed('shift'):
                self.position_moved += 5000
                mixer.music.set_pos(self.get_current_position() // 1000)
            else:
                self.btn_next_click()
        elif event.name == 'stop media' and event.event_type == keyboard.KEY_DOWN:
            self.show_name.emit()
        else:
            # keyboard.unhook_all()
            # keyboard.play([event])
            # keyboard.hook(lambda e: self.kb_handler(e))
            pass

    def save_data(self):
        with open('playlist.mplpl', 'w') as f:
            f.write(json.dumps({
                'repeat_mode': self.repeat_mode,
                'play_mode': self.play_mode,
                'sorting_mode': self.sorting_mode,
                'current_item': self.current_idx,
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
                if _.type == mixer.music.get_endevent():
                    self.song_ended.emit()
            time.sleep(0.05)

    def on_song_ended(self):
        self.btn_next_click()
        if self.repeat_mode == 'one':
            self.btn_prev_click()

    def update_pos(self):
        self.slider_out.setValue(self.get_current_position())
        self.lblTimeCurr.setText(f'{self.get_current_position() // 1000 // 60}:{self.get_current_position() // 1000 % 60}')

    @no_error
    def btn_next_click(self):
        next_ = self.current_idx + 1

        if next_ >= len(self.songs):
            next_ -= len(self.songs)

        self.current_idx = next_
        self.match_current()
        self.save_data()

    @no_error
    def btn_prev_click(self):
        next_ = self.current_idx - 1
        if next_ < 0:
            next_ += len(self.songs)

        self.current_idx = next_
        self.match_current()
        self.save_data()

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
        self.save_data()

    def btn_sorting_click(self):
        if self.sorting_mode == 'A2Z':
            self.sorting_mode = 'Z2A'
        elif self.sorting_mode == 'Z2A':
            self.sorting_mode = 'shuffle'
        elif self.sorting_mode == 'shuffle':
            self.sorting_mode = 'A2Z'

        self.apply_sort()

        self.btn_sorting.setIcon(QIcon(QPixmap(f'images/sorting_{self.sorting_mode}.png')))
        self.save_data()

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

    @no_error
    def match_current(self):
        for i in self.songs:
            i.setStyleSheet('')

        self.songs[self.current_idx].setStyleSheet('background-color: yellow;')
        self.lblSinger.setText(self.current.singer)
        self.lblTitle.setText(self.current.name)
        self.slider_in.setMaximum(round(self.current.duration * 1000))
        self.slider_out.setMaximum(round(self.current.duration * 1000))
        self.lblTimeEnd.setText(f'{int(self.current.duration // 60)}:{int(self.current.duration % 60)}')
        self.slider_in.setMinimum(0)
        self.slider_out.setMinimum(0)

        mixer.music.load(self.current.filename)

        mixer.music.play()
        self.position_moved = 0
        if self.play_mode == 'pause':
            mixer.music.pause()

        if self.name_window is not None:
            if self.name_window.isVisible():
                try:
                    self.name_window.close()
                except Exception as e:
                    print(e)
            self.name_window = None
        self.show_name.emit()

    def closeEvent(self, event):
        self.stopped = True
        time.sleep(0.1)
        self.save_data()
        if self.name_window:
            self.name_window.close()
        event.accept()

    def song_clicked(self, song):
        for i in range(len(self.songs)):
            if self.songs[i].song is song:
                self.current_idx = i
                break
        self.match_current()

    @property
    def current(self):
        return self.songs[self.current_idx].song

    def slider_move(self, value):
        try:
            self.position_moved += value - self.get_current_position()
            mixer.music.set_pos((self.get_current_position()) // 1000)
        except pygame.error:
            print('Error')