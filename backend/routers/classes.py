"""
班级管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Class, LessonPlan, Report, School, Student, TestRecord, TrainingPlan
from config import BASE_DIR

router = APIRouter()

# 加载国标评分标准
with open(os.path.join(BASE_DIR, "national_fitness_standard.json"), 'r', encoding='utf-8') as f:
    STANDARD_DATA = json.load(f)

# Pydantic模型
class ClassCreate(BaseModel):
    """创建班级请求"""
    school_name: str
    grade_level: str  # primary/junior/senior
    grade_name: str   # 一年级/初一/高一等
    class_name: str   # 班级名称
    test_projects: List[str]  # 体测项目列表

class ClassResponse(BaseModel):
    """班级响应"""
    id: int
    name: str
    grade_level: str
    grade_name: str
    test_projects: List[str]
    student_count: int
    
    class Config:
        from_attributes = True

@router.post("/create", response_model=ClassResponse)
async def create_class(
    class_data: ClassCreate,
    db: Session = Depends(get_db)
):
    """
    创建班级（初始化配置流程）
    
    步骤：
    1. 选择学段
    2. 选择年级
    3. 输入班级名称
    4. 勾选体测项目
    """
    # 创建或获取学校
    school = db.query(School).filter(School.name == class_data.school_name).first()
    if not school:
        school = School(name=class_data.school_name)
        db.add(school)
        db.commit()
        db.refresh(school)
    
    # 创建班级
    new_class = Class(
        school_id=school.id,
        name=class_data.class_name,
        grade_level=class_data.grade_level,
        grade_name=class_data.grade_name,
        test_projects=class_data.test_projects
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    
    return ClassResponse(
        id=new_class.id,
        name=new_class.name,
        grade_level=new_class.grade_level,
        grade_name=new_class.grade_name,
        test_projects=new_class.test_projects,
        student_count=0
    )

@router.get("/test-projects/{grade_name}")
async def get_test_projects(grade_name: str):
    """
    获取指定年级的体测项目列表
    
    根据年级返回可选的体测项目
    """
    grade_mapping = STANDARD_DATA["grade_mapping"]
    
    if grade_name not in grade_mapping:
        raise HTTPException(status_code=404, detail="年级不存在")
    
    grade_info = grade_mapping[grade_name]
    level = grade_info["level"]
    
    # 根据学段返回不同的项目
    if level == "primary":
        if grade_info["number"] <= 2:
            projects = STANDARD_DATA["test_projects"]["primary_1_2"]
        elif grade_info["number"] <= 4:
            projects = STANDARD_DATA["test_projects"]["primary_3_4"]
        else:
            projects = STANDARD_DATA["test_projects"]["primary_5_6"]
    else:
        # 初中、高中
        projects = {
            "男生": STANDARD_DATA["test_projects"]["junior_senior_male"],
            "女生": STANDARD_DATA["test_projects"]["junior_senior_female"]
        }
    
    return {
        "grade_name": grade_name,
        "grade_level": level,
        "test_projects": projects
    }

@router.get("/list", response_model=List[ClassResponse])
async def list_classes(db: Session = Depends(get_db)):
    """获取所有班级列表"""
    classes = db.query(Class).all()
    
    result = []
    for cls in classes:
        student_count = db.query(Student).filter(Student.class_id == cls.id).count()
        result.append(ClassResponse(
            id=cls.id,
            name=cls.name,
            grade_level=cls.grade_level,
            grade_name=cls.grade_name,
            test_projects=cls.test_projects,
            student_count=student_count
        ))
    
    return result

@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: int, db: Session = Depends(get_db)):
    """获取班级详情"""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    student_count = db.query(Student).filter(Student.class_id == cls.id).count()
    
    return ClassResponse(
        id=cls.id,
        name=cls.name,
        grade_level=cls.grade_level,
        grade_name=cls.grade_name,
        test_projects=cls.test_projects,
        student_count=student_count
    )


@router.delete("/{class_id}")
async def delete_class(class_id: int, db: Session = Depends(get_db)):
    """删除班级及其学生、成绩、方案、教案和报告。"""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    student_ids = [row[0] for row in db.query(Student.id).filter(Student.class_id == class_id).all()]
    student_count = len(student_ids)

    try:
        db.query(Report).filter(Report.class_id == class_id).delete(synchronize_session=False)
        db.query(LessonPlan).filter(LessonPlan.class_id == class_id).delete(synchronize_session=False)
        if student_ids:
            db.query(Report).filter(Report.student_id.in_(student_ids)).delete(synchronize_session=False)
            db.query(TrainingPlan).filter(TrainingPlan.student_id.in_(student_ids)).delete(synchronize_session=False)
            db.query(TestRecord).filter(TestRecord.student_id.in_(student_ids)).delete(synchronize_session=False)
            db.query(Student).filter(Student.id.in_(student_ids)).delete(synchronize_session=False)
        db.delete(cls)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="班级删除失败，原有数据未被修改")

    return {
        "message": "班级已删除",
        "class_id": class_id,
        "deleted_students": student_count,
    }
