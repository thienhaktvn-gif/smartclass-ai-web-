# 16 môn x 16 câu trắc nghiệm + 3 tự luận, đều là dữ liệu MINH HỌA.
import json
from pathlib import Path
FACTS=json.loads((Path(__file__).parent/'bank16_data.json').read_text(encoding='utf-8'))

def build_exam(subject):
    facts=FACTS[subject]
    questions=[]
    for i,(term,definition) in enumerate(facts):
        # four definition distractors, deterministic balanced correct label
        options=[facts[(i+offset)%16][1] for offset in (0,3,7,11)]
        shift=i%4
        options=options[shift:]+options[:shift]
        correct='ABCD'[options.index(definition)]
        questions.append({'subject':subject,'grade':'8','topic':'Khái niệm cơ bản','content':f'Phát biểu nào đúng về “{term}”?',
         'a':options[0],'b':options[1],'c':options[2],'d':options[3],'answer':correct,
         'difficulty':'Nhận biết','explanation':definition,'origin':'demo-16x19'})
    essays=[
     f'Giải thích khái niệm {facts[0][0]} và nêu một ví dụ minh họa phù hợp với môn {subject}.',
     f'So sánh {facts[3][0]} với {facts[4][0]}; nêu điểm giống và khác nhau (nếu có), lấy ví dụ.',
     f'Vận dụng hiểu biết về {facts[8][0]} để đề xuất một tình huống hoặc hoạt động học tập thực tiễn.'
    ]
    return questions,essays
