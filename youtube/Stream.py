import threading
import ffmpeg
import time
import re
import datetime
import os
import psutil

from tinydb import TinyDB, Query, where


class Stream:
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    TBL_NAME = 'process'
    DB_FILE_PATH = './db/db.json'

    sleep = 5

    def __init__(self, input_file, output, key, loop):
        self.input_file = input_file
        self.output = output
        self.key = key
        self.loop = loop
        self.db = TinyDB(self.DB_FILE_PATH)

    def run(self, ):
        is_active, stream_info = self.is_active_stream(self.key)
        if is_active and psutil.pid_exists(stream_info['pid']):
            return True

        process = self.start_stream(self.input_file, self.output + self.key, self.loop)
        now = datetime.datetime.now()
        date_time = now.strftime("%Y%m%d-%H%M%S")
        log_file = 'ffmpeg-' + date_time + '.log'
        timecode = self.current_timecode(log_file)
        db = self.db.table(self.TBL_NAME)
        db.remove((where('key') == self.key))
        db.insert({
            'key': self.key, 'pid': process.pid, 'status': self.STATUS_ACTIVE, 'log': log_file, 'to_start': timecode
        })
        threading.Thread(target=self.stream_listener, args=(process, log_file)).start()
        return True

    @staticmethod
    def start_stream(input_file, output, loop, timecode='00:00:00'):
        process = (
            ffmpeg.input(
                input_file,
                re=None,
                hwaccel='cuvid',
                # vcodec='h264_cuvid',
                report=None,
                loglevel='40',
                stream_loop=loop,
                ss=timecode
            ).output(
                output,
                vcodec='h264_nvenc',
                r='30',
                b="2500k",
                format='flv'
            ).run_async(quiet=False)
        )

        return process

    @staticmethod
    def current_timecode(log_file):
        timecode = '00:00:00'

        if os.path.isfile(log_file):
            file = open(log_file, 'r')
            text = file.read()
            file.close()
            matches = re.findall(r"time=\w+.\w+.\w+.\w+", text)
            timecode = matches[-1][5:13]

        return timecode

    @staticmethod
    def is_crush(log_file):
        error_messages = [
            'libcuda.so.1'
        ]
        if os.path.isfile(log_file):
            file = open(log_file, 'r')
            text = file.read()
            file.close()
            for val in error_messages:
                error = re.search(val, text)
                if error:
                    return True
                return False
        return False

    def stream_listener(self, process, log_file):

        while True:
            time.sleep(self.sleep)

            print(process.pid)
            if process.poll() is not None:
                if self.is_crush(log_file):
                    os.remove(log_file)
                    timecode = self.current_timecode(log_file)
                    process = self.start_stream(self.input_file, self.output + self.key, self.loop, timecode)
                    tbl = self.db.table(self.TBL_NAME)
                    now = datetime.datetime.now()
                    date_time = now.strftime("%Y%m%d-%H%M%S")
                    log_file = 'ffmpeg-' + date_time + '.log'
                    tbl.update(
                        {'status': self.STATUS_ACTIVE, 'to_start': timecode, 'pid': process.pid, 'log': log_file},
                        where('key') == self.key
                    )
                else:
                    tbl = self.db.table(self.TBL_NAME)
                    tbl.remove((Query().pid == process.pid))
                    os.remove(log_file)
                    break

    def is_active_stream(self, key):
        process = Query()
        tbl = self.db.table(self.TBL_NAME)
        result = tbl.search((process.key == key) & (process.status == self.STATUS_ACTIVE))
        if not result:
            return False, None

        return True, result[0]

    def get_streams(self):
        process = Query()
        tbl = self.db.table(self.TBL_NAME)
        return tbl.all()

    def get_stream_by_key(self, key):
        process = Query()
        tbl = self.db.table(self.TBL_NAME)
        return tbl.search((process.key == key))

    def get_now_time_code(self, key):
        strm = self.get_stream_by_key(key)
        textfile = open(strm[0]['log'], 'r')
        filetext = textfile.read()
        textfile.close()
        matches = re.findall(r"time=\w+.\w+.\w+.\w+", filetext)
        return matches[-1][5:13]

    def stop(self, key):
        strm = self.get_stream_by_key(key)
        stream = strm[0]
        os.system("kill -s KILL " + str(stream['pid']))

        # timecode = self.current_timecode(stream['log'])
        # tbl = self.db.table(self.TBL_NAME)
        # tbl.update({'status': self.STATUS_INACTIVE, 'to_start': timecode}, where('key') == self.key)

        return True

    def restart(self, key):
        is_active, stream_info = self.is_active_stream(key)
        if not is_active:
            return False, "Stream is not active"
        timecode = self.get_now_time_code(key)
        self.stop(key)

        timeList = [stream_info['to_start'], timecode]

        sum = datetime.timedelta()
        for i in timeList:
            (h, m, s) = i.split(':')
            d = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(s))
            sum += d
        new_timecode = str(sum)
        process = start_stream(new_timecode)
        threading.Thread(target=self.stream_listener, args=(process,)).start()

        return True, "Stream has been restart"
