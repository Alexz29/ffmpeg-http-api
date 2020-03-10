import threading
import ffmpeg
import time
import re
import os
import psutil

import sqlite3


class Stream:
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_MANUAL_STOPPED = 'manual_stopped'
    STATUS_SUCCESS_STOPPED = 'success_stopped'
    TBL_NAME = 'streams'
    DB_FILE_PATH = './db/db.sqlite'

    sleep = 5

    def __init__(self, input_file, output, key, loop):
        self.input_file = input_file
        self.output = output
        self.key = key
        self.loop = loop

        self.conn = sqlite3.connect(self.DB_FILE_PATH)
        self.c = self.conn.cursor()

    def db(self, sql, params, fetch_type=None):
        conn = sqlite3.connect(self.DB_FILE_PATH)
        c = conn.cursor()
        c.execute(sql, params)
        conn.commit()

        if fetch_type is None:
            return True

        func = getattr(c, fetch_type)

        return func()

    @property
    def run(self, ):
        is_active, stream_info = self.is_active_stream(self.key)

        if is_active and psutil.pid_exists(stream_info[2]):
            print("=============================================")
            print('STREAM ALREADY EXIST')
            print("=============================================")
            return True

        process, log_file = self.start_stream(self.input_file, self.output, self.key, self.loop)
        timecode = self.current_timecode(log_file)

        sql = "DELETE FROM streams where key = ?"
        self.db(sql, (self.key,))

        sql = "INSERT INTO streams(key, pid, status, log, to_start) VALUES (?, ?, ?, ?, ?)"
        self.db(sql, (self.key, process.pid, self.STATUS_ACTIVE, log_file, timecode,))

        threading.Thread(target=self.stream_listener, args=(process, log_file)).start()

        return True

    @staticmethod
    def start_stream(input_file, output, key, loop, timecode='00:00:00'):
        process = (
            ffmpeg.input(
                input_file,
                re=None,
                hwaccel='cuvid',
                # vcodec='h264_cuvid',
                report=None,
                loglevel='40',
                stream_loop=loop,
                ss=timecode,
            ).output(
                output + key,
                vcodec='h264_nvenc',
                r='30',
                b="2500k",
                format='flv'
            ).run_async(quiet=False)
        )
        time.sleep(5)
        _string = os.popen('grep -rn -i "live2/' + key + '" . -m 1').read()
        log_file = _string[2:28]

        return process, log_file

    @staticmethod
    def current_timecode(log_file):
        timecode = '00:00:00'
        if os.path.isfile(log_file):
            file = open(log_file, 'r')
            text = file.read()
            file.close()
            matches = re.findall(r"time=\w+.\w+.\w+.\w+", text)
            if matches:
                timecode = matches[-1][5:13]
        return timecode

    @staticmethod
    def is_crush(log_file):
        error_messages = [
            'libcuda.so.1',
            'av_interleaved_write_frame',
            'Failed creating CUDA',
            'Invalid data found when processing input',
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

    def stream_listener(self, process, log_file):
        while True:
            time.sleep(self.sleep)
            if process.poll() is not None:
                stream = self.db("SELECT * FROM streams WHERE key=? ", (self.key,), 'fetchone')
                if self.is_crush(log_file) and stream[3] != self.STATUS_MANUAL_STOPPED:
                    print("=============================================")
                    print('INCORRECT STOPPED')
                    print("log file: " + log_file)
                    timecode = self.current_timecode(log_file)
                    print("TIMECODE:" + timecode)
                    os.remove(log_file)
                    print('TRY TO START')
                    process, log_file = self.start_stream(self.input_file, self.output, self.key, self.loop, timecode)
                    sql = "UPDATE streams SET status = ?, to_start = ?, pid = ?, log = ?  WHERE key=? "
                    self.db(sql, (self.STATUS_ACTIVE, timecode, process.pid, log_file, self.key,))
                    print("=============================================")
                else:
                    print("=============================================")
                    print('CORRECT STOPPED')
                    sql = "DELETE FROM streams where pid = ?"
                    self.db(sql, (process.pid,))

                    if os.path.isfile(log_file):
                        os.remove(log_file)

                    print("=============================================")
                    break

    def is_active_stream(self, key):

        sql = "SELECT * FROM streams WHERE key = ? AND status = ? LIMIT 1"
        stream = self.db(sql, (key, self.STATUS_ACTIVE), 'fetchone')

        if not stream:
            return False, None

        return True, stream

    def get_streams(self):
        return self.db("SELECT * FROM streams", (), 'fetchall')

    def stop(self, key):
        stream = self.db("SELECT * FROM streams WHERE key=? ", (key,), 'fetchone')
        if stream:
            os.system("kill -s KILL " + str(stream[2]))
            timecode = self.current_timecode(stream[4])
            self.db("UPDATE streams SET status = ?, to_start = ? WHERE key=? ", (
                self.STATUS_MANUAL_STOPPED, timecode, self.key,
            ))

        return True

    # def restart(self, key):
    #     is_active, stream_info = self.is_active_stream(key)
    #     if not is_active:
    #         return False, "Stream is not active"
    #     timecode = self.get_now_time_code(key)
    #     self.stop(key)
    #
    #     timeList = [stream_info['to_start'], timecode]
    #
    #     sum = datetime.timedelta()
    #     for i in timeList:
    #         (h, m, s) = i.split(':')
    #         d = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(s))
    #         sum += d
    #     new_timecode = str(sum)
    #     process = start_stream(new_timecode)
    #     threading.Thread(target=self.stream_listener, args=(process,)).start()
    #
    #     return True, "Stream has been restart"
