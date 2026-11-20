"""
演示数据初始化脚本 - 将 demo_data.json 导入数据库
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal, init_db, engine
from models import Base, School, Class, Student, TestRecord
from scoring_service import ScoringService
from config import BASE_DIR


def load_demo_data():
    """仅在空数据库中加载演示数据，绝不覆盖客户已有信息。"""
    init_db()
    db = SessionLocal()

    try:
        if db.query(Class).count() or db.query(Student).count():
            return {
                "success": False,
                "error": "数据库中已有班级或学生，已取消载入，原有数据未受影响",
            }

        # 读取演示数据
        demo_file = os.path.join(BASE_DIR, "demo_data.json")
        with open(demo_file, 'r', encoding='utf-8') as f:
            demo = json.load(f)

        # 创建学校
        school = School(name=demo["school_name"])
        db.add(school)
        db.commit()
        db.refresh(school)
        school_id = school.id
        school_name = school.name

        total_students = 0
        total_records = 0

        for class_data in demo["classes"]:
            # 映射年级名称
            grade_raw = class_data["grade"]
            grade_name = _map_grade_name(grade_raw)

            # 构建体测项目列表（中文名）
            test_projects = _extract_test_projects(class_data)

            # 创建班级
            cls = Class(
                school_id=school_id,
                name=class_data["class_name"],
                grade_level=class_data["grade_level"],
                grade_name=grade_name,
                test_projects=test_projects
            )
            db.add(cls)
            db.commit()
            db.refresh(cls)
            class_id = cls.id

            for stu_data in class_data["students"]:
                student = Student(
                    class_id=class_id,
                    student_id=stu_data["student_id"],
                    name=stu_data["name"],
                    gender=stu_data["gender"],
                    special_conditions=stu_data.get("special_conditions", [])
                )
                db.add(student)
                db.commit()
                db.refresh(student)
                student_id = student.id
                total_students += 1

                for rec in stu_data["test_records"]:
                    # 转换成绩并计算得分
                    grades_dict, avg_score = ScoringService.convert_all_scores(
                        rec["scores"],
                        grade_name,
                        stu_data["gender"]
                    )

                    test_record = TestRecord(
                        student_id=student_id,
                        test_date=datetime.strptime(rec["test_date"], "%Y-%m-%d"),
                        test_type=rec["test_type"],
                        scores=rec["scores"],
                        grades=grades_dict,
                        total_score=avg_score,
                        total_grade=ScoringService.calculate_total_grade(avg_score)
                    )
                    db.add(test_record)
                    total_records += 1

            db.commit()

        return {
            "success": True,
            "school": school_name,
            "classes": len(demo["classes"]),
            "students": total_students,
            "test_records": total_records
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def _map_grade_name(grade_raw):
    """将演示数据中的年级名称映射为国标年级名称"""
    mapping = {
        "小学一年级": "一年级", "小学二年级": "二年级", "小学三年级": "三年级",
        "小学四年级": "四年级", "小学五年级": "五年级", "小学六年级": "六年级",
        "初中一年级": "初一", "初中二年级": "初二", "初中三年级": "初三",
        "高中一年级": "高一", "高中二年级": "高二", "高中三年级": "高三",
    }
    return mapping.get(grade_raw, grade_raw)


def _extract_test_projects(class_data):
    """从班级数据中提取体测项目中文名列表（排除身高体重，它们仅用于BMI计算）"""
    if class_data["students"] and class_data["students"][0]["test_records"]:
        scores = class_data["students"][0]["test_records"][0]["scores"]
        key_map = {
            "vital_capacity": "肺活量",
            "50m_run": "50米跑", "sit_and_reach": "坐位体前屈",
            "standing_long_jump": "立定跳远", "1min_rope_skip": "1分钟跳绳",
            "1min_sit_ups": "1分钟仰卧起坐", "1000m_run": "1000米跑",
            "800m_run": "800米跑", "pull_ups": "引体向上",
        }
        return [key_map[k] for k in scores.keys() if k in key_map]
    return []


if __name__ == "__main__":
    result = load_demo_data()
    print(result)
