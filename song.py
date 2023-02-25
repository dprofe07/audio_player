class Song:
    def __init__(self, name, filename, singer, duration):
        self.name = name
        self.filename = filename
        self.singer = singer
        self.duration = duration

    def formatted_duration(self):
        return f'{round(self.duration) // 60}:{round(self.duration % 60)}'

    def formatted_name(self, separator='—'):
        return f'{self.singer} {separator} {self.name} {separator} {self.formatted_duration()}'