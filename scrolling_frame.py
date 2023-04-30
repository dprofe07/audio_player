from PyQt5.QtWidgets import QFrame, QVBoxLayout, QWidget, QScrollArea


class ScrollingFrame(QWidget):
    def __init__(self, items: list = (), parent=None):
        super().__init__(parent)
        self.items = items


        self.scroll_content = QWidget()

        self.list_box = QVBoxLayout()
        self.scroll_content.setLayout(self.list_box)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_content)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.scroll_area)
        self.setLayout(self.main_layout)

        self.redraw_items()

    def add_item(self, item):
        self.list_box.addWidget(item)
        self.items.append(item)

    def redraw_items(self):
        for i in reversed(range(self.list_box.count())):
            a = self.list_box.itemAt(i).widget()

            if a:
                a.setParent(None)
                self.list_box.removeWidget(a)
        for i in self.items:
            self.list_box.addWidget(i)
            self.list_box.addStretch(1)
