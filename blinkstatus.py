import sys

from blinkdetector import BlinkDetector
import cv2
import time
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QMessageBox


class BlinkObject:
    def __init__(self, time, status):
        self.time, self.status = time, status

    @staticmethod
    def delta_seconds(a, b):
        return a.time - b.time


class StatusTracker:
    def __init__(self, keep_seconds=60):
        self.history = []
        self.keep_seconds = keep_seconds

    def _history_time_span(self):
        return BlinkObject.delta_seconds(self.history[-1], self.history[0])

    def add(self, blinkobj):
        self.history.append(blinkobj)
        if self.history and self._history_time_span() > self.keep_seconds:
            self.history.pop(0)

    def _total_blinks(self):
        time_pool = set()
        for i in range(len(self.history) - 1):
            if self.history[i].status == BlinkDetector.EYE_OPEN and \
                    self.history[i + 1].status == BlinkDetector.EYE_CLOSE:
                time_pool.add(int(self.history[i].time + 0.5))
        return len(time_pool)

    def reset(self):
        self.history = []

    @property
    def blinks_per_minute(self):
        if len(self.history) < 100:
            return -1
        blinks = self._total_blinks()
        span = self._history_time_span()
        return int(blinks * 60 / span + 0.5)


class BlinkStatus:
    UNKNOWN = 0
    SAFE = 1
    DANGER = 2

    def __init__(self, safe_boundary=15, camid=1, videopath=''):
        cap = None
        if camid >= 0:
            cap = camid
        if videopath:
            cap = videopath
        self.cap = cv2.VideoCapture(cap)

        self.bkdet = BlinkDetector()
        self.stt = StatusTracker()
        self.safe_boundary = safe_boundary

    @property
    def blinks_per_minute(self):
        return self.stt.blinks_per_minute

    def proc(self):
        _, bgr = self.cap.read()
        if bgr is not None:
            self.stt.add(BlinkObject(
                time.time(), self.bkdet.get_status(bgr)))
        else:
            raise Exception('can not read frame')

    def reset(self):
        self.stt.reset()

    @property
    def status(self):
        bpm = self.blinks_per_minute
        if bpm < 0:
            return self.UNKNOWN
        return self.SAFE if bpm >= self.safe_boundary else self.DANGER


if __name__ == '__main__':
    bs = BlinkStatus(safe_boundary=25, camid=0)
    app = QApplication([])
    first_danger = True
    while True:
        try:
            bs.proc()
            print(f"每分钟眨眼： {bs.stt.blinks_per_minute}", end='\r')
            if bs.status == bs.DANGER and first_danger:
                first_danger = False
            elif bs.status == bs.DANGER:
                window = QWidget()
                layout = QVBoxLayout()
                label = QLabel(f"每分钟眨眼：{bs.stt.blinks_per_minute}")
                layout.addWidget(label)
                ok = QPushButton('OK')
                exit = QPushButton('EXIT')


                def on_button_clicked_ok():
                    alert = QMessageBox()
                    alert.setText('不要再犯！')
                    alert.exec()
                    window.close()

                def on_button_clicked_exit():
                    alert = QMessageBox()
                    alert.setText('确定退出吗？')
                    alert.exec()
                    window.close()
                    sys.exit()

                ok.clicked.connect(on_button_clicked_ok)
                exit.clicked.connect(on_button_clicked_exit)
                layout.addWidget(ok)
                layout.addWidget(exit)
                window.setLayout(layout)
                window.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
                window.show()
                app.exec_()
                bs.reset()
                first_danger = True
        except Exception as e:
            print(e)
            break
