import json
import os
import random

import pygame
from PyQt5.QtGui import QIcon, QPixmap
from pygame import mixer
from tinytag import tinytag

from no_error import no_error
from song import Song
from song_item import SongItem


class Playlist:
    def __init__(self, window, filename, name, repeat_mode, play_mode, sorting_mode, current_item, current_pos, songs):
        self.mw = window
        self.name = name
        self.filename = filename
        self.repeat_mode = repeat_mode
        self.play_mode = play_mode
        self.sorting_mode = sorting_mode
        self.current_idx = current_item
        self.position_moved = current_pos
        self.songs = songs

    @property
    def current_song(self):
        return self.songs[self.current_idx].song

    def draw_buttons(self):
        self.mw.btn_play_pause.setIcon(QIcon(QPixmap(f'images/{"play" if self.play_mode == "pause" else "pause"}.png')))
        self.mw.btn_repeater.setIcon(QIcon(QPixmap(f'images/repeat_{self.repeat_mode}.png')))
        self.mw.btn_sorting.setIcon(QIcon(QPixmap(f'images/sorting_{self.sorting_mode}.png')))

    @staticmethod
    def from_dict(window, playlist_filename, dct):
        pl = Playlist(window, playlist_filename, dct['name'], dct['repeat_mode'], dct['play_mode'], dct['sorting_mode'],
                      dct['current_item'], dct['current_pos'], [])
        pl.songs = pl.process_songs(dct['songs'])
        return pl

    def process_songs(self, filenames):
        res = []
        for filename in filenames:
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
                res.append(song_item)
        return res

    @no_error
    def match_current(self):
        for i in self.songs:
            i.setStyleSheet('')
        self.songs[self.current_idx].setStyleSheet('background-color: yellow;')
        self.mw.lblSinger.setText(self.current_song.singer)
        self.mw.lblTitle.setText(self.current_song.name)
        self.mw.slider_in.setMaximum(round(self.current_song.duration * 1000))
        self.mw.slider_out.setMaximum(round(self.current_song.duration * 1000))
        self.mw.lblTimeEnd.setText(f'{int(self.current_song.duration // 60)}:{int(self.current_song.duration % 60)}')
        self.mw.slider_in.setMinimum(0)
        self.mw.slider_out.setMinimum(0)

        mixer.music.load(self.current_song.filename)

        mixer.music.play()

        if self.play_mode == 'pause':
            mixer.music.pause()

        if self.mw.name_window is not None:
            if self.mw.name_window.isVisible():
                try:
                    self.mw.name_window.close()
                except Exception as e:
                    print(e)
            self.mw.name_window = None
        self.mw.show_name.emit()

    def save_data(self):
        with open(f'{self.filename}.mplpl', 'w') as f:
            f.write(json.dumps({
                'repeat_mode': self.repeat_mode,
                'play_mode': self.play_mode,
                'sorting_mode': self.sorting_mode,
                'current_item': self.current_idx,
                'current_pos': self.position_moved + mixer.music.get_pos(),
                'songs': [i.song.filename for i in self.songs],
                'name': self.name,
            }))

    def next_song(self):
        next_ = self.current_idx + 1

        if next_ >= len(self.songs):
            next_ -= len(self.songs)

        self.current_idx = next_
        self.match_current()
        self.save_data()

    def prev_song(self):
        next_ = self.current_idx - 1

        if next_ < 0:
            next_ += len(self.songs)

        self.current_idx = next_
        self.match_current()
        self.save_data()

    def change_repeater_mode(self):
        if self.repeat_mode == 'no':
            self.repeat_mode = 'one'
        else:
            self.repeat_mode = 'no'
        self.mw.btn_repeater.setIcon(QIcon(QPixmap(f'images/repeat_{self.repeat_mode}.png')))

    def change_play_mode(self):
        if self.play_mode == 'play':
            self.play_mode = 'pause'
        else:
            self.play_mode = 'play'

        if self.play_mode == 'pause':
            mixer.music.pause()
        elif self.play_mode == 'play':
            mixer.music.unpause()

        self.mw.btn_play_pause.setIcon(QIcon(QPixmap(f'images/{"play" if self.play_mode == "pause" else "pause"}.png')))
        self.save_data()

    def change_sorting_mode(self):
        if self.sorting_mode == 'A2Z':
            self.sorting_mode = 'Z2A'
        elif self.sorting_mode == 'Z2A':
            self.sorting_mode = 'shuffle'
        elif self.sorting_mode == 'shuffle':
            self.sorting_mode = 'A2Z'

        self.apply_sort()

        self.mw.btn_sorting.setIcon(QIcon(QPixmap(f'images/sorting_{self.sorting_mode}.png')))
        self.save_data()

    def apply_sort(self):
        if self.sorting_mode == 'shuffle':
            random.shuffle(self.songs)
            self.mw.scroll_view.items = self.songs
            self.mw.scroll_view.redraw_items()
        elif self.sorting_mode == 'A2Z':
            self.songs.sort(key=lambda i: i.song.formatted_name())
            self.mw.scroll_view.items = self.songs
            self.mw.scroll_view.redraw_items()
        elif self.sorting_mode == 'Z2A':
            self.songs.sort(key=lambda i: i.song.formatted_name(), reverse=True)
            self.mw.scroll_view.items = self.songs
            self.mw.scroll_view.redraw_items()

    def song_clicked(self, song):
        for i in range(len(self.songs)):
            if self.songs[i].song is song:
                self.current_idx = i
                break
        self.position_moved = 0
        self.match_current()

    def set_as_active_playlist(self):
        self.mw.scroll_view.items = self.songs
        self.mw.scroll_view.redraw_items()

        self.match_current()
        try:
            mixer.music.set_pos(self.position_moved // 1000)
        except pygame.error:
            print('Troubles')

        self.draw_buttons()

    def add_song(self):
        dial = self.mw.get_songs_list()

        for filename in dial:
            try:
                tag = tinytag.TinyTag.get(filename)
            except FileNotFoundError:
                print(f'File not found: {filename}')
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
        self.mw.scroll_view.redraw_items()
        self.save_data()

    def delete_song(self):
        self.songs.pop(self.current_idx)
        if self.current_idx >= len(self.songs):
            self.current_idx = len(self.songs) - 1
        self.mw.scroll_view.redraw_items()
        self.match_current()
        self.save_data()

    def renew_playlist(self):
        self.songs.clear()

        self.add_song()
        self.mw.scroll_view.redraw_items()

        self.match_current()
        self.save_data()

    def remove_file(self):
        os.remove(self.filename + '.mplpl')
