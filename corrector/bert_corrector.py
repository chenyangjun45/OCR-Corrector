#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Title   : 利用BERT模型进行纠错
@File    : bert_corrector.py
@Author  : Tian
@Time    : 2020/06/16 5:04 下午
@Version : 1.0
"""
import re
import logging
import time
# from corrector.base_corrector import BaseCorrector
# from corrector.bert_modeling.masked_lm import MaskedLM, MaskedLMConfig
from base_corrector import BaseCorrector
from bert_modeling.masked_lm import MaskedLM, MaskedLMConfig
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
class BertCorrector(BaseCorrector):
    """
    BERT纠错
    """
    def __init__(self, config: MaskedLMConfig):
        super().__init__(config=config)
        self.bert = MaskedLM(config)
        self.accept_correct = FilterCurves.curve_02

    def correct_all(self, texts, error_positions):
        """
        kc = BertCorrector(MaskedLMConfig)
        kc.correct_all(['本着平等、白愿、诚信、互利的原则，一致同意本合同内容，并共同遵守。',
        '无效、重大暇疵或不符合乙方其他规定的债权资产，'
        ... '乙方有权拒绝，不子初始登'],[[5],[5, 31]])
        ['本着平等、自愿、诚信、互利的原则，一致同意本合同内容，并共同遵守。',
        '无效、重大瑕疵或不符合乙方其他规定的债权资产，乙方有权拒绝，不予初始登']
        """

        # bert接收阿拉伯数字会出错（返回长度不定的阿拉伯数字），所以先去掉
        rep = {'1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六',
               '7': '七', '8': '八', '9': '九', '0': '零'}
        rep = dict((re.escape(k), v) for k, v in rep.items())
        number = re.compile("|".join(rep.keys()))
        texts_numfree = [number.sub(lambda m: rep[re.escape(m.group(0))], s) for s in texts]
        start_1 = time.time()
        bert_out = self.bert.find_topn_candidates(texts_numfree, error_positions)
        end_1 = time.time()
        logger.info("获取bert候选集的耗时：" + str(end_1-start_1))
        start_2 = time.time()
        for i in range(len(texts)):
            try:
                err_pos = error_positions[i]
                logger.debug('纠正【%s】错误位置【%s】', texts[i], err_pos)
                origin = list(texts[i])
                for j, e in enumerate(err_pos):
                    # 不修正数字
                    if self.regulars['number'].match(origin[e]):
                        logger.debug('原字【%s】为数字，不纠错', origin[e])
                        continue

                    for k in range(self.config.topn):
                        confidence = bert_out[i][j][k][1]   # 第i个句子，第j个错字，第k个预测结果，第1个元素（confidence）
                        pred = bert_out[i][j][k][0]  # 第i个句子，第j个错字，第k个预测结果，第0个元素（pred）
                        char_similarity = self.char_sim.shape_similarity(pred, origin[e])
                        logger.debug('原字【%s】bert预测结果：【%s】,confidence：【%f】，char_similarity:【%f】',
                                     origin[e], pred, confidence, char_similarity)

                        # 检查预测结果
                        if origin[e] == pred:
                            continue
                        if not self.check_bert_out(origin[e], pred):   # 处理不能接受接错结果的情况
                            continue
                        if self.accept_correct(confidence, char_similarity):   # confidence 和 similarity 联合判断是否接受
                            logger.debug('※ 接受纠错 ※')
                            origin[e] = pred
                            break
                texts[i] = ''.join(origin)

            except Exception:
                import traceback
                logger.error(traceback.format_exc())
                logger.error('纠错出现错误，跳过【%s】',texts[i])
        end_2 = time.time()
        logger.info("字形相似度计算等操作的耗时：" + str(end_2 - start_2))
        return texts

    # bert需要重写是否纠错的过滤
    def do_correct_filter(self, text):
        # 包含字母的不纠错
        # if re.search(self.regulars['alphabet'], text):
        #     return False
        # 包含小于3个汉字的不纠错
        if len(re.findall(self.regulars['chinese'], text)) < 2:
            return False
        # 超过最大长度的暂时跳过，因为这样的情况应该很少，仅防止出错
        if len(text) > self.config.max_seq_length - 2:
            logger.error('句子长度超过最大长度%d，跳过纠错', self.config.max_seq_length - 2)
            return False
        return True

    def check_bert_out(self, original, corrected_to):
        if corrected_to == '[UNK]':
            return False
        if '#' in corrected_to:
            return False
        if len(corrected_to) != len(original):
            return False
        if re.search(self.regulars['alphabet'], corrected_to):
            return False
        # 如果correct_to是繁体字，则不接受纠错
        if re.match(self.regulars['traditional'], corrected_to):
            return False
        return True


    @staticmethod
    def recover_number(sen1, sen2):
        """把句子1中的数字赋值到句子2中，用于恢复数字"""
        new_sen = sen2
        for i, s in enumerate(sen1):
            if u'\u0030' <= s <= u'\u0039':
                new_sen = new_sen[:i] + s + new_sen[i + 1:]

        return new_sen



class FilterCurves(object):
    """
    决定是否接受BERT预测结果的依据。
    详情见论文：https://www.aclweb.org/anthology/D19-5522/
    """
    def __init__(self):
        pass

    @staticmethod
    def curve_null(confidence, similarity):
        """This curve is used when no filter is applied"""
        return True

    @staticmethod
    def curve_full(confidence, similarity):
        """This curve is used to filter out everything"""
        return False

    @staticmethod
    def curve_02(confidence, similarity):
        flag1 = confidence + similarity - 1 >= 0
        flag2 = confidence - 0.05 >= 0
        # 原始代码的参数
        # flag3 = similarity - 0.4 >= 0
        flag3 = similarity - 0.2 >= 0

        if flag1 and flag2 and flag3:
            return True

        return False
if __name__=="__main__":
    corrector = BertCorrector(MaskedLMConfig)
    # result = corrector.correct(['我爱北京大安门'],[[0.99, 0.99, 0.99, 0.99, 0.56, 0.99, 0.99]])
    # result = corrector.correct(['甲元声像图'],[[0.99, 0.56, 0.99, 0.99, 0.99]])
    # result = corrector.correct(['非姜缩性胃炎'],[[0.99, 0.56, 0.99, 0.99, 0.99, 0.99]])
    # print(result)
    # result = corrector.correct(['双侧乳腺肺乳期政变'],[[0.99, 0.99, 0.99, 0.99, 0.56, 0.99, 0.99, 0.56, 0.99]])
    # print(result)
    # result = corrector.correct(['考患双侧甲状腺腺癌可能性大'],[[0.99, 0.56, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99]])
    # print(result)
    # result = corrector.correct(['肝脏术见明显异常'],[[0.99,0.99, 0.56, 0.99, 0.99, 0.99, 0.99, 0.99]])
    # print(result)
    # result = corrector.correct(['性质待定，建议进一苏检查'],[[0.99,0.99, 0.99, 0.99, 0.99, 0.99, 0.99,0.99,0.99, 0.56,0.99,0.99]])
    # print(result)
    # result = corrector.correct(['性质待定，建议进一苏检查'])
    # result = corrector.correct(['甲状腺体职增大件不均顾政安'])
    # result = corrector.correct(['前列腺钙化壮'])
    # print(result)
    # result = corrector.correct(['脑动脉解样硬化'])
    # print(result)
    # result = corrector.correct(['脑概元'])
    # print(result)
    # result = corrector.correct(['双侧卵集未见异常声像'])
    # print(result)
    # result = corrector.correct(['非苓缩性胃炎'])
    # print(result)
    # result = corrector.correct(['甲状腺实质殊浸性病变'])
    # print(result)
    # result = corrector.correct(['胆囊多发降起样病变'])
    # print(result)
    # result = corrector.correct(['混合特'])
    # print(result)
    # result = corrector.correct(['考患左侧卵集酶胎瘤可能'])
    logger.info("计时开始")
    start_time = time.time()
    result = corrector.correct(['非姜缩性胃炎'],[[0.99, 0.56, 0.99, 0.99, 0.99, 0.99]])
    result = corrector.correct(['双侧乳腺肺乳期政变'],[[0.99, 0.99, 0.99, 0.99, 0.56, 0.99, 0.99, 0.56, 0.99]])
    result = corrector.correct(['考患双侧甲状腺腺癌可能性大'],[[0.99, 0.56, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99]])
    result = corrector.correct(['脑动脉解样硬化'])
    end_time = time.time()
    logger.info("耗时为："+str(end_time-start_time))
    logger.info(result)
