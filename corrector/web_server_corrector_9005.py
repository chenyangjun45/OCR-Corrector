import json
import os
import tornado
from tornado.web import RequestHandler
from tornado.escape import json_decode, to_unicode
import traceback
from logger_config import base_logger
from bert_corrector import BertCorrector
from bert_modeling.masked_lm import MaskedLM, MaskedLMConfig
import time
# 加载模型，这个要放在外面
corrector = BertCorrector(MaskedLMConfig)

class CorrectorHandler(RequestHandler):

    def data_received(self, chunk):
        pass

    def get(self, *args, **kwargs):
        self.render('find_answer.html')

    def post(self, *args, **kwargs):
        self.use_write()

    def get_json_argument(self, name, default=None):
        args = json_decode(self.request.body)
        name = to_unicode(name)
        if name in args:
            return args[name]
        elif default is not None:
            return default
        else:
            raise tornado.web.MissingArgumentError(name)

    def use_write(self):
        try:
            try:
                raw_content = self.get_json_argument('content')
            except:
                raw_content = self.get_argument('content')
            start_time = time.time()
            # 注意限制文本的长度
            result = corrector.correct([raw_content])
            end_time = time.time()
            base_logger.info("纠错的耗时：" + str(end_time - start_time))
        except Exception as e:
            base_logger.warning("Fail to correct the content!")
            base_logger.warning(traceback.print_exc())
            base_logger.warning(e)
            result = ""

        json_data = {
            "corrector_result":result
        }
        self.write(json.dumps(json_data, ensure_ascii=False))

def make_app():
    setting = dict(
        template_path=os.path.join(os.path.dirname(__file__), 'templates'),
        static_path=os.path.join(os.path.dirname(__file__), 'static')
    )
    return tornado.web.Application(
        [(r'/correct', CorrectorHandler)],
        **setting
    )


if __name__ == '__main__':
    app = make_app()
    app.listen(9005)
    tornado.ioloop.IOLoop.current().start()

