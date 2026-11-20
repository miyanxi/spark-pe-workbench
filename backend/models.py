"""
数据模型定义
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import Base

class School(Base):
    """学校模型"""
    __tablename__ = "schools"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    classes = relationship("Class", back_populates="school")

class Class(Base):
    """班级模型"""
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    name = Column(String(50), nullable=False)  # 班级名称
    grade_level = Column(String(20), nullable=False)  # 学段：primary/junior/senior
    grade_name = Column(String(20), nullable=False)  # 年级名称：如"初一"、"高一"
    test_projects = Column(JSON)  # 体测项目列表
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    school = relationship("School", back_populates="classes")
    students = relationship("Student", back_populates="class_info")

class Student(Base):
    """学生模型"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    student_id = Column(String(20), nullable=False)  # 学号
    name = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False)  # 男/女
    special_conditions = Column(JSON)  # 特殊体质标签
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    class_info = relationship("Class", back_populates="students")
    test_records = relationship("TestRecord", back_populates="student")

class TestRecord(Base):
    """测试记录模型"""
    __tablename__ = "test_records"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    test_date = Column(DateTime, nullable=False)
    test_type = Column(String(50))  # 测试类型：期初测试、期末测试等
    scores = Column(JSON)  # 各项目成绩（JSON格式）
    grades = Column(JSON)  # 各项目等级（JSON格式）
    total_score = Column(Float)  # 总分
    total_grade = Column(String(20))  # 总等级
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    student = relationship("Student", back_populates="test_records")

class TrainingPlan(Base):
    """训练方案模型"""
    __tablename__ = "training_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    plan_name = Column(String(100))
    plan_type = Column(String(50))  # 方案类型：短期/中期/假期
    duration = Column(String(50))  # 周期时长
    exercises = Column(JSON)  # 训练动作列表
    encouragement = Column(Text)  # 个性化鼓励语
    created_at = Column(DateTime, default=datetime.utcnow)

class LessonPlan(Base):
    """教案模型"""
    __tablename__ = "lesson_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    plan_name = Column(String(100))
    teaching_objective = Column(Text)  # 教学目标
    preparation_part = Column(Text)  # 准备部分
    main_part = Column(Text)  # 基本部分
    ending_part = Column(Text)  # 结束部分
    homework = Column(Text)  # 课后作业
    weak_items = Column(JSON)  # 薄弱项列表
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    """报告模型"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50))  # 报告类型：个人/班级
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    content = Column(Text)  # 报告内容
    comment = Column(Text)  # 评语
    created_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    grade_level = Column(String(20))  # 学段
    category = Column(String(50))  # 分类：田径/球类/体操/安全等
    created_at = Column(DateTime, default=datetime.utcnow)