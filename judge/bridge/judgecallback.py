from judgehandler import JudgeHandler
import logging

logger = logging.getLogger('judge.bridge')


class DjangoJudgeHandler(JudgeHandler):
    def on_grading_begin(self, packet):
        JudgeHandler.on_grading_begin(self, packet)

    def on_grading_end(self, packet):
        JudgeHandler.on_grading_end(self, packet)

    def on_compile_error(self, packet):
        JudgeHandler.on_compile_error(self, packet)

    def on_test_case(self, packet):
        JudgeHandler.on_test_case(self, packet)
