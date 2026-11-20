"""
训练方案生成API路由
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
from models import Student, Class, TestRecord, TrainingPlan
from deepseek_client import deepseek_client

router = APIRouter()

class TrainingPlanRequest(BaseModel):
    """训练方案请求"""
    student_id: int
    plan_type: str  # 短期/中期/假期

class TrainingPlanResponse(BaseModel):
    """训练方案响应"""
    id: int
    plan_name: str
    plan_type: str
    duration: str
    exercises: List[dict]
    encouragement: str

@router.post("/generate", response_model=TrainingPlanResponse)
async def generate_training_plan(
    request: TrainingPlanRequest,
    db: Session = Depends(get_db)
):
    """
    生成个性化训练方案
    
    根据学生薄弱项自动匹配动作组合
    """
    # 获取学生信息
    student = db.query(Student).filter(Student.id == request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # 获取班级信息
    cls = db.query(Class).filter(Class.id == student.class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    # 获取学生最近的测试记录
    latest_record = db.query(TestRecord).filter(
        TestRecord.student_id == request.student_id
    ).order_by(TestRecord.test_date.desc()).first()
    
    # 识别薄弱项
    weak_items = []
    if latest_record and latest_record.grades:
        for project, grade_info in latest_record.grades.items():
            if not isinstance(grade_info, dict):
                continue
            score = grade_info.get("score")
            try:
                numeric_score = float(score)
            except (TypeError, ValueError):
                # 身高、体重等基础数据可能没有独立分数，不应导致方案生成失败。
                continue
            if numeric_score < 70:
                weak_items.append(project)
    
    # 构建AI提示词
    system_prompt = """你是一位专业的体育训练教练，擅长制定个性化的训练方案。

请根据学生的以下信息，生成一个具体的训练方案。

输出格式要求（严格遵守）：

第一行：方案名称
第二行：训练周期

然后是训练动作表格，格式如下（每行一个动作，用|分隔）：
动作名称|组数|次数/时长|休息间隔|动作要领

例如：
深蹲跳|3组|每组10次|30秒|下蹲至大腿与地面平行，爆发跳起
弓步交替跳|3组|每腿8次|30秒|前膝不过脚尖，交替跳换

表格之后，输出安全提醒（2-3条）。

最后一两句话给这个学生一句温暖真诚的鼓励，不要加任何标题，自然地写就行。

注意：
- 根据学段调整动作难度（小学趣味性、初中进阶、高中专项）
- 考虑特殊体质学生，避免高风险动作
- 训练强度适中，循序渐进
- 鼓励语要提到学生名字，语气像朋友一样自然"""

    user_prompt = f"""
学生信息：
- 姓名：{student.name}
- 性别：{student.gender}
- 年级：{cls.grade_name}
- 薄弱项目：{", ".join(weak_items) if weak_items else "无"}
- 特殊体质：{", ".join(student.special_conditions) if student.special_conditions else "无"}
- 训练类型：{request.plan_type}

请生成训练方案。"""

    # 调用AI生成训练方案
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    ai_response = deepseek_client.chat(messages)
    
    if ai_response is None:
        raise HTTPException(status_code=500, detail="AI生成失败")
    
    # 解析AI响应（简化版，实际需要更复杂的解析逻辑）
    # 这里假设AI返回的是结构化文本，需要解析
    # 实际应用中可以让AI返回JSON格式
    
    # 解析AI响应：提取鼓励语（最后一段）
    ai_lines = [l for l in ai_response.strip().split('\n') if l.strip()]
    encouragement = ""
    main_content = ai_response

    if len(ai_lines) >= 2:
        last_line = ai_lines[-1].strip()
        # 如果最后一行像鼓励语（没有数字编号开头、没有标题标记）
        if last_line and not last_line[0].isdigit() and not last_line.startswith('#') and not last_line.startswith('【') and len(last_line) < 80:
            encouragement = last_line
            main_content = '\n'.join(ai_lines[:-1])

    # 创建训练方案记录
    training_plan = TrainingPlan(
        student_id=request.student_id,
        plan_name=f"{student.name}的{request.plan_type}训练方案",
        plan_type=request.plan_type,
        duration="2周" if request.plan_type == "短期" else "1个月",
        exercises=[{"content": main_content}],
        encouragement=encouragement if encouragement else f"{student.name}，加油！坚持训练，你一定能进步！"
    )
    db.add(training_plan)
    db.commit()
    db.refresh(training_plan)
    
    return TrainingPlanResponse(
        id=training_plan.id,
        plan_name=training_plan.plan_name,
        plan_type=training_plan.plan_type,
        duration=training_plan.duration,
        exercises=training_plan.exercises,
        encouragement=training_plan.encouragement
    )

@router.get("/list/{student_id}")
async def list_training_plans(student_id: int, db: Session = Depends(get_db)):
    """获取学生的训练方案列表"""
    plans = db.query(TrainingPlan).filter(TrainingPlan.student_id == student_id).all()
    
    return {
        "student_id": student_id,
        "plans": [
            {
                "id": plan.id,
                "plan_name": plan.plan_name,
                "plan_type": plan.plan_type,
                "duration": plan.duration,
                "created_at": str(plan.created_at)
            }
            for plan in plans
        ]
    }
