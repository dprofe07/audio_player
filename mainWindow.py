import json
import os.path
import random
import threading
import time

import keyboard
import pygame.event
from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSlider, QFileDialog, QComboBox, \
    QMessageBox, QInputDialog
from pygame import mixer

from name_window import NameWindow
from no_error import no_error
from playlist import Playlist
from scrolling_frame import ScrollingFrame

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
        self.stopped = False

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

        self.hboxControls.addStretch(1)

        # Controls:

        self.btn_repeater = QPushButton(QIcon('images/repeat_no.png'), '')
        self.btn_repeater.clicked.connect(lambda e: self.current_playlist.change_repeater_mode())

        self.btn_prev = QPushButton(QIcon('images/previous.png'), '')
        self.btn_prev.clicked.connect(lambda e: self.current_playlist.prev_song())

        self.btn_play_pause = QPushButton(QIcon('images/play.png'), '')
        self.btn_play_pause.clicked.connect(lambda e: self.current_playlist.change_play_mode())

        self.btn_next = QPushButton(QIcon('images/next.png'), '')
        self.btn_next.clicked.connect(lambda e: self.current_playlist.next_song())

        self.btn_sorting = QPushButton(QIcon('images/sorting_A2Z.png'), '')
        self.btn_sorting.clicked.connect(lambda e: self.current_playlist.change_sorting_mode())

        self.slider_volume = QSlider(Qt.Vertical)
        self.slider_volume.setMinimum(0)
        self.slider_volume.setMaximum(100)
        self.slider_volume.setValue(int(pygame.mixer.music.get_volume() * 100))
        self.slider_volume.setFixedHeight(60)
        self.slider_volume.valueChanged.connect(self.slider_volume_changed)

        for i in [self.btn_repeater, self.btn_prev, self.btn_play_pause, self.btn_next, self.btn_sorting]:
            self.hboxControls.addWidget(i)
            i.setFixedHeight(75)
            i.setFixedWidth(75)
            i.setIconSize(QSize(60, 60))

        self.hboxControls.addWidget(self.slider_volume)
        self.hboxControls.addStretch(1)

        self.slider_out = QSlider(Qt.Horizontal)
        self.vbox.addWidget(self.slider_out)

        self.slider_in = QSlider(Qt.Horizontal)
        self.slider_in.valueChanged.connect(self.slider_move)
        self.slider_moved_before = False

        self.vbox.addWidget(self.slider_in)

        self.hbox_time = QHBoxLayout()
        self.vbox.addLayout(self.hbox_time)

        self.lblTimeCurr = QLabel("0:00")
        self.hbox_time.addWidget(self.lblTimeCurr)

        self.hbox_time.addStretch(1)

        self.lblTimeEnd = QLabel("0:00")
        self.hbox_time.addWidget(self.lblTimeEnd)

        self.hboxPlaylists = QHBoxLayout()
        self.vbox.addLayout(self.hboxPlaylists)

        self.cmbPlaylists = QComboBox()
        self.cmbPlaylists.currentIndexChanged.connect(self.playlist_changed)
        self.hboxPlaylists.addWidget(self.cmbPlaylists)

        self.btn_add_playlist = QPushButton('+')
        self.btn_add_playlist.clicked.connect(self.add_playlist)

        self.btn_rename_playlist = QPushButton('/')
        self.btn_rename_playlist.clicked.connect(self.rename_playlist)

        self.btn_remove_playlist = QPushButton('-')
        self.btn_remove_playlist.clicked.connect(self.remove_playlist)

        for i in [self.btn_remove_playlist, self.btn_add_playlist, self.btn_rename_playlist]:
            i.setFixedWidth(30)
            self.hboxPlaylists.addWidget(i)

        self.scroll_view = ScrollingFrame([])
        self.vbox.addWidget(self.scroll_view)

        self.hbox_playlist_controls = QHBoxLayout()
        self.vbox.addLayout(self.hbox_playlist_controls)

        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(lambda e: self.current_playlist.add_song())
        self.hbox_playlist_controls.addWidget(self.btn_add)

        self.btn_del = QPushButton("Delete")
        self.btn_del.clicked.connect(lambda e: self.current_playlist.delete_song())
        self.hbox_playlist_controls.addWidget(self.btn_del)

        self.btn_renew = QPushButton("Пересоздать")
        self.btn_renew.clicked.connect(lambda e: self.current_playlist.renew_playlist())
        self.hbox_playlist_controls.addWidget(self.btn_renew)

        keyboard.hook(lambda q: self.kb_handler(q))
        # keyboard.on_release(lambda q: [print(q), self.kb_handler(q)])
        # keyboard.on_press_key('play/pause media', self.kb_handler)
        # Parameters

        exists_data = os.path.exists('data.mpldt')
        if exists_data:
            with open('data.mpldt') as f:
                if f.read() == '':
                    exists_data = False

        if not exists_data:
            with open('data.mpldt', 'w') as f:
                f.write(
                    json.dumps(
                        {
                            'playlists': ['default_playlist'],
                            'current_playlist_idx': 0,
                            'volume': 0.5
                        }
                    )
                )
            with open('default_playlist.mplpl', 'w') as f:
                songs = self.get_songs_list()
                f.write(
                    json.dumps(
                        {
                            'repeat_mode': 'no',
                            'play_mode': 'pause',
                            'sorting_mode': 'A2Z',
                            'current_item': 0,
                            'current_pos': 0,
                            'songs': songs,
                            'name': 'Стандартный плейлист',
                        }
                    )
                )
        else:
            playlist_exists = True
            with open('data.mpldt') as f:
                data = json.loads(f.read())
                if len(data.get('playlists', [])) < data.get('current_playlist_idx', 1_000_000_000):
                    playlist_exists = False

            if not playlist_exists:
                with open('default_playlist.mplpl', 'w') as f:
                    songs = self.get_songs_list()
                    f.write(
                        json.dumps(
                            {
                                'repeat_mode': 'no',
                                'play_mode': 'pause',
                                'sorting_mode': 'A2Z',
                                'current_item': 0,
                                'current_pos': 0,
                                'songs': songs,
                                'name': 'Стандартный плейлист',
                            }
                        )
                    )

        with open('data.mpldt') as f:
            data = json.loads(f.read())

            self.slider_volume.setValue(int(data.get('volume', 0.5) * 100))

            playlist_names = data['playlists']
            self.playlists = []
            idx = self.current_playlist_idx = data['current_playlist_idx']
            for playlist in playlist_names:
                try:
                    open(f'{playlist}.mplpl')
                except FileNotFoundError:
                    QMessageBox(QMessageBox.Icon.Warning, 'Error', f"Can't read playlist '{playlist}'",
                                QMessageBox.StandardButton.Ok, self).show()
                    continue

                with open(f'{playlist}.mplpl') as f:
                    try:
                        playlist_data = json.loads(f.read())
                    except json.JSONDecodeError:
                        QMessageBox(QMessageBox.Icon.Warning, 'Error', f"Can't read playlist '{playlist}'", QMessageBox.StandardButton.Ok, self).show()
                        continue
                    self.playlists.append(Playlist.from_dict(self, playlist, playlist_data))
            if self.current_playlist_idx >= len(self.playlists):
                self.current_playlist_idx = len(self.playlists) - 1

            self.cmbPlaylists.clear()
            for p in self.playlists:
                self.cmbPlaylists.addItem(p.name)

            self.cmbPlaylists.setCurrentIndex(idx)

        self.current_playlist.set_as_active_playlist()

        threading.Thread(target=self.song_check).start()
        threading.Thread(target=self.song_check_end).start()

    @property
    def current_playlist(self):
        return self.playlists[self.current_playlist_idx]

    def get_songs_list(self):
        return QFileDialog.getOpenFileNames(
                self, "Выберите файлы",
                os.path.expanduser("~") + '/Music',
                "Music files (*.mp3);;All Files (*)"
            )[0]

    def get_current_position(self):
        return mixer.music.get_pos() + self.current_playlist.position_moved

    def on_show_name(self):
        if self.name_window is not None and not self.name_window.stopped:
            self.name_window.stopped = True
            if self.name_window.isVisible():
                self.name_window.close()
        elif True:
            self.name_window = NameWindow(
                self.name_window_closed, self.current_playlist.current_idx,  # self.current.formatted_name('::'),
                self.current_playlist.songs,
                lambda: self.get_current_position() / 1000, lambda: self.current_playlist.current_song.duration
            )
            self.name_window.show()

    def on_name_window_closed(self):
        self.name_window = None

    def kb_handler(self, event: keyboard.KeyboardEvent):
        if event.name == 'play/pause media' and event.event_type == keyboard.KEY_DOWN:
            self.btn_play_pause_click()
        elif event.name == 'previous track' and event.event_type == keyboard.KEY_DOWN:
            if keyboard.is_pressed('shift'):
                self.current_playlist.position_moved -= 5000
                mixer.music.set_pos(self.get_current_position() // 1000)
            else:
                self.btn_prev_click()
        elif event.name == 'next track' and event.event_type == keyboard.KEY_DOWN:
            if keyboard.is_pressed('shift'):
                self.current_playlist.position_moved += 5000
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
        self.current_playlist.save_data()
        with open('data.mpldt', 'w') as f:
            f.write(
                json.dumps(
                    {
                        'playlists': [i.filename for i in self.playlists],
                        'current_playlist_idx': self.current_playlist_idx,
                        'volume': pygame.mixer.music.get_volume(),
                    }
                )
            )

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
        if self.current_playlist.repeat_mode == 'one':
            self.btn_prev_click()

    def update_pos(self):
        self.slider_out.setValue(self.get_current_position())
        self.lblTimeCurr.setText(f'{self.get_current_position() // 1000 // 60}:{self.get_current_position() // 1000 % 60}')

    @no_error
    def btn_next_click(self):
        self.current_playlist.next_song()

    @no_error
    def btn_prev_click(self):
        self.current_playlist.prev_song()

    def btn_repeater_click(self):
        self.current_playlist.change_repeater_mode()

    def btn_play_pause_click(self):
        self.current_playlist.change_play_mode()

    def btn_sorting_click(self):
        self.current_playlist.change_sorting_mode()

    def closeEvent(self, event):
        self.stopped = True
        time.sleep(0.1)
        self.save_data()
        if self.name_window:
            self.name_window.close()
        for pl in self.playlists:
            pl.save_data()
        event.accept()

    def slider_move(self, value):
        if not self.slider_moved_before:
            self.slider_moved_before = True
            return
        try:
            self.current_playlist.position_moved += value - self.get_current_position()
            mixer.music.set_pos(self.get_current_position() // 1000)
        except pygame.error:
            print('Error')

    def playlist_changed(self):
        self.current_playlist.position_moved = self.get_current_position()
        self.current_playlist.save_data()
        self.current_playlist_idx = self.cmbPlaylists.currentIndex()
        self.save_data()
        self.current_playlist.set_as_active_playlist()

    def add_playlist(self):
        playlist_name = QInputDialog.getText(self, 'Создание плейлиста', 'Введите название плейлиста')
        if not playlist_name[1]:
            return

        pl = Playlist(
            self,
            'playlist_' + ''.join(random.choice('1234567890qwertyuiopasdfghjklzxcvbnm') for _ in range(20)),
            playlist_name[0],
            'no', 'pause', 'A2Z', 0, 0, []
        )
        pl.songs = pl.process_songs(self.get_songs_list())
        self.current_playlist.save_data()

        self.playlists.append(pl)
        self.current_playlist_idx = len(self.playlists) - 1
        self.cmbPlaylists.addItem(playlist_name[0])
        self.cmbPlaylists.setCurrentIndex(self.current_playlist_idx)
        self.save_data()

    def remove_playlist(self):
        if len(self.playlists) == 1:
            a = QMessageBox(QMessageBox.Warning, "Ошибка", "Нельзя удалить последний плейлист", QMessageBox.Ok, self)
            a.show()
            return
        for i in self.current_playlist.songs:
            i.deleteLater()
            i.setParent(None)
        cur_idx = self.current_playlist_idx
        self.current_playlist.remove_file()
        self.playlists.pop(cur_idx)
        self.cmbPlaylists.removeItem(cur_idx)
        if cur_idx >= len(self.playlists):
            cur_idx = len(self.playlists) - 1
        self.cmbPlaylists.setCurrentIndex(cur_idx)
        self.current_playlist.set_as_active_playlist()
        self.save_data()

    def rename_playlist(self):
        playlist_name = QInputDialog.getText(self, 'Переименование плейлиста', 'Введите название плейлиста')
        if not playlist_name[1]:
            return
        playlist_name = playlist_name[0]
        self.cmbPlaylists.setItemText(self.current_playlist_idx, playlist_name)
        self.current_playlist.name = playlist_name

    def slider_volume_changed(self):
        pygame.mixer.music.set_volume(self.slider_volume.value() / 100)