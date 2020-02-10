import threading
import ffmpeg
import time
import re
import datetime
import os

from tinydb import TinyDB, Query, where


class Stream:
    """
    Приветствю Вас в нарнии о мой господин!
    Если ты видишь эти строки, беги отсюда, как можно быстрее!
    Данный быдлокод очень помогает стримить видео потоки на сраный ютубчик

    вот один из скотских примеров использования чудесной поделки:

    Начать отправку потока:
        stream = Stream('./1.mp4', 'rtmp://a.rtmp.youtube.com/live2/', '04a6-scmz-btz5-8rda', 0)
        stream.run()

    Перезапустить поток:
        stream = Stream('./1.mp4', 'rtmp://a.rtmp.youtube.com/live2/', '04a6-scmz-btz5-8rda', 0)
        print(stream.restart('04a6-scmz-btz5-8rda'))

    Остановить поток:
        stream = Stream('./1.mp4', 'rtmp://a.rtmp.youtube.com/live2/', '04a6-scmz-btz5-8rda', 0)
        print(stream.stop('04a6-scmz-btz5-8rda'))

    """
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    TBL_NAME = 'process'
    DB_FILE_PATH = './db/db.json'

    def __init__(self, input_file, output, key, loop):
        self.input_file = input_file
        self.output = output
        self.key = key
        self.loop = loop
        self.db = TinyDB(self.DB_FILE_PATH)

    def run(self, ):
        """
        Главная функция для запуска стрима

        :return: string PID тдентификатор процесса
        """
        is_active, stream_info = self.is_active_stream(self.key)
        if not is_active:
            process = self.start_stream()
            threading.Thread(target=self.stream_listener, args=(process,)).start()
            return process.pid
        return stream_info['pid']

    def stream_listener(self, process):
        """
        Функция для отслеживания активности прецесса конвертации.
        Когда процесс закончился, в базе происходит изменение статуса на STATUS_INACTIVE.
        Шаг дискоретизации 5 секунд

        :param process: object Запущенный процесс
        :return:
        """
        pid = process.pid
        while True:
            strm = self.get_stream_by_key(self.key)
            if process.poll() is not None:
                tbl = self.db.table(self.TBL_NAME)
                tbl.update({'status': self.STATUS_INACTIVE, 'to_start':'00:00:00' }, where('pid') == pid)
                os.remove(strm[0]['log'])
                break
            time.sleep(5)

    def start_stream(self, timecode='00:00:00'):
        """
        Функция самого запуска стрима

        :return:
        """
        tbl = self.db.table(self.TBL_NAME)
        tbl.remove((where('status') == self.STATUS_INACTIVE) & (where('key') == self.key))
        process = (
            ffmpeg
                .input(self.input_file,
                    re=None,
                    hwaccel='cuvid',
                    c:v='h264_cuvid'
                    report=None,
                    loglevel='40',
                    stream_loop=self.loop,
                    ss=timecode
                )
                .output(
                    self.output + self.key,
                    vcodec='h264_nvenc',
                    # pix_fmt='yuv420p',
                    # maxrate='2M',
                    # bufsize='2M',
                    r='30',
                    b="2500k",  # bitrate 2500 kbit/s youtube recommendation
                    # segment_time='1',
                    format='flv'
                )
                .run_async(quiet=False)
        )
        now = datetime.datetime.now()
        date_time = now.strftime("%Y%m%d-%H%M%S")
        log_file = 'ffmpeg-' + date_time + '.log'
        # делаем запись в базе
        tbl.insert({
            'key': self.key,
            'pid': process.pid,
            'status': self.STATUS_ACTIVE,
            'log': log_file,
            'to_start': timecode
        })
        return process

    def is_active_stream(self, key):
        """
        Функция для проверки активности процесса.
        Если процесс активено то она возвращает запись данного проуесса из бд

        :param key: string ключ трансляции
        :return:
        """
        process = Query()
        tbl = self.db.table(self.TBL_NAME)
        result = tbl.search((process.key == key) & (process.status == self.STATUS_ACTIVE))
        if not result:
            return False, None

        return True, result[0]

    def get_stream_by_key(self, key):
        """
        Функция возвращает из бд запись с процессом

        :param key: string ключ трансляции
        :return: array
        """
        process = Query()
        tbl = self.db.table(self.TBL_NAME)
        return tbl.search((process.key == key))

    def get_now_time_code(self, key):
        """
        Функция возвращает таймкод на котором остановился процесс

        :param key: string ключ трансляции
        :return: string
        """
        strm = self.get_stream_by_key(key)
        textfile = open(strm[0]['log'], 'r')
        filetext = textfile.read()
        textfile.close()
        matches = re.findall(r"time=\w+.\w+.\w+.\w+", filetext)
        return matches[-1][5:13]

    def stop(self, key):
        """
        Функция останавливает стрим

        :param key: string ключ трансляции
        :return:
        """
        strm = self.get_stream_by_key(key)
        os.system("kill -s KILL " + str(strm[0]['pid']))
        tbl = self.db.table(self.TBL_NAME)
        timecode = self.get_now_time_code(key)
        tbl.update({'status': self.STATUS_INACTIVE, 'to_start': timecode }, where('key') == self.key)

        return True

    def restart(self, key):
        """
        Перезапуск активного потока

        :param key:
        :return:
        """
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
        process = self.start_stream(new_timecode)
        threading.Thread(target=self.stream_listener, args=(process,)).start()

        return True, "Stream has been restart"

