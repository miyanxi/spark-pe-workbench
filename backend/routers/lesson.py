"""
智能备课API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Class, Student, TestRecord, LessonPlan
from deepseek_client import deepseek_client

router = APIRouter()

class LessonPlanRequest(BaseModel):
    """教案生成请求"""
    class_id: int
    teaching_objective: Optional[str] = None  # 教学目标（可选）

class LessonPlanResponse(BaseModel):
    """教案响应"""
    id: int
    plan_name: str
    teaching_objective: str
    preparation_part: str
    main_part: str
    ending_part: str
    homework: str
    weak_items: List[str]

@router.post("/generate", response_model=LessonPlanResponse)
async def generate_lesson_plan(
    request: LessonPlanRequest,
    db: Session = Depends(get_db)
):
    """
    生成智能教案
    
    自动读取班级弱项，生成四段式结构化教案
    """
    # 获取班级信息
    cls = db.query(Class).filter(Class.id == request.class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    # 获取班级学生
    students = db.query(Student).filter(Student.class_id == request.class_id).all()
    
    # 识别班级薄弱项
    weak_items = {}
    test_projects = cls.test_projects
    
    for project in test_projects:
        excellent_count = 0
        good_count = 0
        pass_count = 0
        total_count = 0
        
        for student in students:
            latest_record = db.query(TestRecord).filter(
                TestRecord.student_id == student.id
            ).order_by(TestRecord.test_date.desc()).first()
            
            if latest_record and latest_record.grades:
                grade_info = latest_record.grades.get(project)
                if grade_info:
                    total_count += 1
                    grade = grade_info.get("grade")
                    if grade == "优秀":
                        excellent_count += 1
                    elif grade == "良好":
                        good_count += 1
                    elif grade == "及格":
                        pass_count += 1
        
        if total_count > 0:
            excellent_rate = (excellent_count + good_count) / total_count
            weak_items[project] = {
                "excellent_rate": round(excellent_rate * 100, 1),
                "is_weak": excellent_rate < 0.6  # 优良率低于60%视为薄弱项
            }
    
    # 筛选出薄弱项
    weak_projects = [k for k, v in weak_items.items() if v["is_weak"]]
    
    # 构建AI提示词
    system_prompt = """你是一位专业的体育教师，擅长编写结构化教案。

请根据班级信息，生成一份四段式结构化教案：

1. 准备部分（10分钟）：
   - 热身活动（慢跑、拉伸等）
   - 体育游戏（趣味性强，适合学段）
   - 队列练习

2. 基本部分（30分钟）：
   - 主教材讲解与示范（根据教学目标）
   - 班级薄弱项针对性强化练习
   - 分层练习建议（按学生能力分组）

3. 结束部分（5分钟）：
   - 拉伸放松
   - 课堂小结
   - 器材回收

4. 课后作业：
   - 针对性微训练建议

注意：
- 根据学段调整内容（小学趣味性、初中进阶、高中专项）
- 薄弱项强化练习要具体、可操作
- 每个部分标注时间分配
- 使用表格或列表呈现，清晰明了"""

    user_prompt = f"""
班级信息：
- 班级名称：{cls.name}
- 年级：{cls.grade_name}
- 学生人数：{len(students)}
- 体测项目：{", ".join(test_projects)}
- 薄弱项：{", ".join(weak_projects) if weak_projects else "无"}
- 教学目标：{request.teaching_objective or "根据班级实际情况制定"}

请生成教案。"""

    # 调用AI生成教案
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    ai_response = deepseek_client.chat(messages)
    
    if ai_response is None:
        raise HTTPException(status_code=500, detail="AI生成失败")
    
    # 解析AI响应为四段
    preparation_part = ""
    main_part = ""
    ending_part = ""
    homework = ""
    
    # 按段落分割，寻找各部分标记
    import re
    sections = re.split(r'(?=([一二三四1-4])[、.．]\s*(?:准备|基本|结束|课后))', ai_response)
    
    # 尝试按常见标题分割
    prep_match = re.search(r'(?:一[、.．]|1[、.．])\s*(?:准备部分|热身部分|准备活动)(.*?)(?=(?:二[、.．]|2[、.．])\s*(?:基本部分|主要部分|基本活动)|$)', ai_response, re.DOTALL)
    main_match = re.search(r'(?:二[、.．]|2[、.．])\s*(?:基本部分|主要部分|基本活动)(.*?)(?=(?:三[、.．]|3[、.．])\s*(?:结束部分|放松部分|结束活动)|$)', ai_response, re.DOTALL)
    end_match = re.search(r'(?:三[、.．]|3[、.．])\s*(?:结束部分|放松部分|结束活动)(.*?)(?=(?:四[、.．]|4[、.．])\s*(?:课后作业|课后练习|作业)|$)', ai_response, re.DOTALL)
    hw_match = re.search(r'(?:四[、.．]|4[、.．])\s*(?:课后作业|课后练习|作业)(.*)', ai_response, re.DOTALL)
    
    if prep_match:
        preparation_part = prep_match.group(1).strip()
        main_part = main_match.group(1).strip() if main_match else ""
        ending_part = end_match.group(1).strip() if end_match else ""
        homework = hw_match.group(1).strip() if hw_match else ""
    else:
        # 无法解析时，整体放入基本部分
        preparation_part = ""
        main_part = ai_response
        ending_part = ""
        homework = ""
    
    # 创建教案记录
    lesson_plan = LessonPlan(
        class_id=request.class_id,
        plan_name=f"{cls.name}体育教案",
        teaching_objective=request.teaching_objective or "根据班级实际情况制定",
        preparation_part=preparation_part,
        main_part=main_part,
        ending_part=ending_part,
        homework=homework,
        weak_items=weak_projects
    )
    db.add(lesson_plan)
    db.commit()
    db.refresh(lesson_plan)
    
    return LessonPlanResponse(
        id=lesson_plan.id,
        plan_name=lesson_plan.plan_name,
        teaching_objective=lesson_plan.teaching_objective,
        preparation_part=lesson_plan.preparation_part,
        main_part=lesson_plan.main_part,
        ending_part=lesson_plan.ending_part,
        homework=lesson_plan.homework,
        weak_items=lesson_plan.weak_items
    )

@router.get("/list/{class_id}")
async def list_lesson_plans(class_id: int, db: Session = Depends(get_db)):
    """获取班级的教案列表"""
    plans = db.query(LessonPlan).filter(LessonPlan.class_id == class_id).all()
    
    return {
        "class_id": class_id,
        "plans": [
            {
                "id": plan.id,
                "plan_name": plan.plan_name,
                "weak_items": plan.weak_items,
                "created_at": str(plan.created_at)
            }
            for plan in plans
        ]
    }

@router.get("/{plan_id}")
async def get_lesson_plan(plan_id: int, db: Session = Depends(get_db)):
    """获取教案详情"""
    plan = db.query(LessonPlan).filter(LessonPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="教案不存在")
    
    return {
        "id": plan.id,
        "plan_name": plan.plan_name,
        "teaching_objective": plan.teaching_objective,
        "preparation_part": plan.preparation_part,
        "main_part": plan.main_part,
        "ending_part": plan.ending_part,
        "homework": plan.homework,
        "weak_items": plan.weak_items,
        "created_at": str(plan.created_at)
    }