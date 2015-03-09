import logging
import threading
import time
import os
from event_socket_server import get_preferred_engine

from judge.models import Judge
from .judgelist import JudgeList

logger = logging.getLogger('judge.bridge')


def reset_judges():
    Judge.objects.update(online=False, ping=None, load=None)


class JudgeServer(get_preferred_engine()):
    def __init__(self, *args, **kwargs):
        super(JudgeServer, self).__init__(*args, **kwargs)
        reset_judges()
        self.judges = JudgeList()
        self.ping_judge_thread = threading.Thread(target=self.ping_judge, args=())
        self.ping_judge_thread.daemon = True
        self.ping_judge_thread.start()

    def on_shutdown(self):
        super(JudgeServer, self).on_shutdown()
        reset_judges()

    def ping_judge(self):
        try:
            while True:
                for judge in self.judges:
                    judge.ping()
                time.sleep(10)
        except:
            logger.exception('Ping error')
            raise


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
    server = JudgeServer(args.judge_host, args.judge_port, JudgeHandler)
    server.serve_forever()


if __name__ == '__main__':
    main()