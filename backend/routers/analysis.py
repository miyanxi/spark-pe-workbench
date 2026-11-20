"""
学情分析API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Class, Student, TestRecord

router = APIRouter()

@router.get("/heatmap/{class_id}")
async def get_class_heatmap(class_id: int, db: Session = Depends(get_db)):
    """
    获取班级热力图数据
    
    返回全班各项目达标率分布
    """
    # 获取班级信息
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    # 获取班级所有学生
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        return {"message": "班级暂无学生"}
    
    # 获取体测项目
    test_projects = cls.test_projects
    
    # 统计各项目达标情况
    heatmap_data = {}
    for project in test_projects:
        excellent_count = 0
        good_count = 0
        pass_count = 0
        fail_count = 0
        
        for student in students:
            # 获取学生最近的测试记录
            latest_record = db.query(TestRecord).filter(
                TestRecord.student_id == student.id
            ).order_by(TestRecord.test_date.desc()).first()
            
            if latest_record and latest_record.grades:
                grade_info = latest_record.grades.get(project)
                if grade_info:
                    grade = grade_info.get("grade")
                    if grade == "优秀":
                        excellent_count += 1
                    elif grade == "良好":
                        good_count += 1
                    elif grade == "及格":
                        pass_count += 1
                    else:
                        fail_count += 1
        
        total = len(students)
        heatmap_data[project] = {
            "优秀": excellent_count,
            "良好": good_count,
            "及格": pass_count,
            "不及格": fail_count,
            "优秀率": round(excellent_count / total * 100, 1) if total > 0 else 0,
            "良好率": round(good_count / total * 100, 1) if total > 0 else 0,
            "及格率": round((excellent_count + good_count + pass_count) / total * 100, 1) if total > 0 else 0,
            "不及格率": round(fail_count / total * 100, 1) if total > 0 else 0
        }
    
    return {
        "class_id": class_id,
        "class_name": cls.name,
        "grade_name": cls.grade_name,
        "student_count": len(students),
        "heatmap_data": heatmap_data
    }

@router.get("/radar/{student_id}")
async def get_student_radar(student_id: int, db: Session = Depends(get_db)):
    """
    获取学生个人能力雷达图数据
    
    综合呈现力量、速度、耐力、柔韧、灵敏五维指标
    """
    # 获取学生信息
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # 获取最近的测试记录
    latest_record = db.query(TestRecord).filter(
        TestRecord.student_id == student_id
    ).order_by(TestRecord.test_date.desc()).first()
    
    if not latest_record:
        return {"message": "学生暂无测试记录"}
    
    # 根据项目类型映射到五维能力
    # 50米跑 -> 速度
    # 立定跳远 -> 力量
    # 1000米/800米 -> 耐力
    # 坐位体前屈 -> 柔韧
    # 仰卧起坐/引体向上 -> 灵敏（或力量）
    
    radar_data = {
        "速度": 0,
        "力量": 0,
        "耐力": 0,
        "柔韧": 0,
        "灵敏": 0
    }
    
    if latest_record.grades:
        for project, grade_info in latest_record.grades.items():
            score = grade_info.get("score", 0)
            
            if "50米跑" in project:
                radar_data["速度"] = score
            elif "立定跳远" in project or "跳绳" in project:
                radar_data["力量"] = score
            elif "1000米" in project or "800米" in project:
                radar_data["耐力"] = score
            elif "坐位体前屈" in project:
                radar_data["柔韧"] = score
            elif "仰卧起坐" in project or "引体向上" in project:
                radar_data["灵敏"] = score
    
    return {
        "student_id": student_id,
        "student_name": student.name,
        "gender": student.gender,
        "test_date": latest_record.test_date,
        "radar_data": radar_data
    }

@router.get("/trend/{student_id}")
async def get_student_trend(student_id: int, db: Session = Depends(get_db)):
    """
    获取学生成绩趋势折线图数据
    
    呈现个人单项成绩跨学期、跨月份的变化曲线
    """
    # 获取学生信息
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # 获取所有测试记录（按时间排序）
    test_records = db.query(TestRecord).filter(
        TestRecord.student_id == student_id
    ).order_by(TestRecord.test_date.asc()).all()
    
    if not test_records:
        return {"message": "学生暂无测试记录"}
    
    # 统计各项目的成绩趋势（仅含有得分的项目）
    trend_data = {}
    for record in test_records:
        if record.grades:
            for project, grade_info in record.grades.items():
                score = grade_info.get("score")
                if score is None:
                    continue  # 跳过身高、体重等无得分项
                if project not in trend_data:
                    trend_data[project] = []
                trend_data[project].append({
                    "date": str(record.test_date),
                    "score": score,
                    "grade": grade_info.get("grade", "")
                })
    
    return {
        "student_id": student_id,
        "student_name": student.name,
        "trend_data": trend_data
    }

@router.get("/warnings/{class_id}")
async def get_warnings(class_id: int, db: Session = Depends(get_db)):
    """
    获取异常预警学生列表
    
    识别连续两次测试成绩下滑超过10%的学生
    """
    # 获取班级所有学生
    students = db.query(Student).filter(Student.class_id == class_id).all()
    
    warning_students = []
    
    for student in students:
        # 获取学生最近两次测试记录
        recent_records = db.query(TestRecord).filter(
            TestRecord.student_id == student.id
        ).order_by(TestRecord.test_date.desc()).limit(2).all()
        
        if len(recent_records) >= 2:
            # 比较总分
            if recent_records[0].total_score and recent_records[1].total_score:
                decline = recent_records[1].total_score - recent_records[0].total_score
                
                if decline > 10:
                    warning_students.append({
                        "student_id": student.id,
                        "student_name": student.name,
                        "gender": student.gender,
                        "previous_score": recent_records[1].total_score,
                        "current_score": recent_records[0].total_score,
                        "decline": round(decline, 1)
                    })
    
    return {
        "class_id": class_id,
        "warning_students": warning_students
    }