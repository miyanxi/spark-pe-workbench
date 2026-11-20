"""Generate reproducible, entirely fictional showcase data using the standard library."""
import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def generate():
    rng = random.Random(20261119)
    result = {'school_name': 'SPARK 演示学校', 'academic_year': '2026-2027', 'classes': []}
    levels = [('小学三年级', 'primary', 3), ('初中一年级', 'junior', 1), ('高中一年级', 'senior', 1)]
    for class_index, (grade, level, number) in enumerate(levels, 1):
        classroom = {'class_id': f'DEMO-C{class_index:02d}', 'class_name': f'{grade}（演示班）', 'grade': grade, 'grade_level': level, 'grade_number': number, 'students': []}
        for local_index in range(1, 11):
            number_id = (class_index - 1) * 10 + local_index
            male = bool(local_index % 2)
            student = {'student_id': f'DEMO-{number_id:03d}', 'name': f'演示学生{number_id:02d}', 'gender': '男' if male else '女', 'special_conditions': [], 'test_records': []}
            for visit, date in enumerate(['2026-03-15', '2026-05-15']):
                scores = {
                    'height': [135, 160, 169][class_index - 1] + local_index % 8 + visit,
                    'weight': [32, 49, 58][class_index - 1] + local_index % 7,
                    'vital_capacity': [1800, 2900, 3500][class_index - 1] + local_index * 35 + visit * 60,
                    '50m_run': round(8.2 + rng.random() * 2.1 - visit * .12, 1),
                    'sit_and_reach': round(8 + rng.random() * 10 + visit * .5, 1),
                }
                if level == 'primary':
                    scores.update({'1min_rope_skip': 95 + local_index * 3 + visit * 6, '1min_sit_ups': 24 + local_index % 12 + visit * 2})
                else:
                    scores['standing_long_jump'] = 170 + local_index * 2 + visit * 3
                    if male:
                        scores.update({'pull_ups': 3 + local_index % 7 + visit, '1000m_run': 250 + local_index * 3 - visit * 5})
                    else:
                        scores.update({'1min_sit_ups': 24 + local_index % 12 + visit * 2, '800m_run': 235 + local_index * 2 - visit * 5})
                student['test_records'].append({'test_date': date, 'test_type': ['演示期初测试', '演示期末测试'][visit], 'scores': scores})
            classroom['students'].append(student)
        result['classes'].append(classroom)
    result['metadata'] = {'created_date': '2026-11-19', 'description': '纯合成演示数据；姓名、学校、编号和成绩均非真实记录，不能用于验证评分标准准确性或提出实际训练处方。', 'total_students': 30, 'synthetic': True, 'generator_seed': 20261119}
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'demo_data.json')
    args = parser.parse_args()
    args.output.write_text(json.dumps(generate(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Generated 3 fictional classes, 30 students and 60 test records.')

if __name__ == '__main__':
    main()
