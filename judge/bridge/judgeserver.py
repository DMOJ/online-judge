import SocketServer
import threading
import time
import os

from Queue import Queue
from django.db import connection
from judge.models import Judge
from judge.caching import update_submission

from .judgelist import JudgeList


def reset_judges():
    Judge.objects.update(online=False, last_connect=None, ping=None, load=None)


class JudgeServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        SocketServer.ThreadingTCPServer.__init__(self, *args, **kwargs)
        reset_judges()
        self.judges = JudgeList()
        self.cache_queue = Queue()
        self.ping_judge_thread = threading.Thread(target=self.ping_judge, args=())
        self.ping_judge_thread.daemon = True
        self.ping_judge_thread.start()
        self.ping_db_thread = threading.Thread(target=self.ping_database, args=())
        self.ping_db_thread.daemon = True
        self.ping_db_thread.start()

    def queue_purge(self, sub):
        self.cache_queue.put((time.time(), sub))

    def purge_thread(self):
        while True:
            t, sub = self.cache_queue.get()
            t += 2
            now = time.time()
            if t > now:
                time.sleep(t - now)
            update_submission(sub)

    def shutdown(self):
        SocketServer.ThreadingTCPServer.shutdown(self)
        reset_judges()

    def ping_judge(self):
        while True:
            for judge in self.judges:
                judge.ping()
            time.sleep(10)

    @staticmethod
    def ping_database():
        while True:
            cursor = connection.cursor()
            cursor.execute('SELECT 1').fetchall()
            time.sleep(1800)


def main():
    import argparse
    import logging
    from judgehandler import JudgeHandler

    format = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
    logging.basicConfig(format=format)
    logging.getLogger().setLevel(logging.INFO)
    handler = logging.FileHandler(os.path.join(os.path.dirname(__file__), 'judgeserver.log'), encoding='utf-8')
    handler.setFormatter(logging.Formatter(format))
    handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)

    parser = argparse.ArgumentParser(description='''
        Runs the bridge between DMOPC website and judges.
    ''')
    parser.add_argument('judge_host', nargs='?', default='127.0.0.1',
                        help='host to listen for the judge')
    parser.add_argument('-p', '--judge-port', type=int, default=9999,
                        help='port to listen for the judge')

    args = parser.parse_args()
    server = JudgeServer((args.judge_host, args.judge_port), JudgeHandler)
    server.serve_forever()


if __name__ == '__main__':
    main()