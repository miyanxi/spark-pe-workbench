"""
报告生成API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Student, Class, TestRecord, Report
from deepseek_client import deepseek_client

router = APIRouter()

class ReportRequest(BaseModel):
    """报告生成请求"""
    report_type: str  # personal/class
    student_id: Optional[int] = None
    class_id: Optional[int] = None

class ReportResponse(BaseModel):
    """报告响应"""
    id: int
    report_type: str
    content: str
    comment: str

@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db)
):
    """
    生成学情报告
    
    支持个人报告（家长通知书）和班级报告（教学总结）
    """
    if request.report_type == "personal":
        # 个人报告
        if not request.student_id:
            raise HTTPException(status_code=400, detail="缺少学生ID")
        
        # 获取学生信息
        student = db.query(Student).filter(Student.id == request.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")
        
        # 获取班级信息
        cls = db.query(Class).filter(Class.id == student.class_id).first()
        
        # 获取测试记录
        test_records = db.query(TestRecord).filter(
            TestRecord.student_id == request.student_id
        ).order_by(TestRecord.test_date.desc()).all()
        
        if not test_records:
            raise HTTPException(status_code=400, detail="学生暂无测试记录")
        
        # 构建AI提示词
        system_prompt = """你是一位温暖有爱的体育教师，正在给学生家长写一封体质健康通知书。

请用像跟家长面对面聊天一样的语气，写一封真诚、温暖的家书，包含：
1. 开头亲切地称呼家长，简单说说孩子近期的体育表现
2. 用通俗的话解释孩子的体质等级和各项成绩，别用冷冰冰的数字堆砌
3. 如果有进步，真心替孩子高兴；如果有退步，温柔地分析原因，不要责备
4. 给出2-3个家长在家就能陪孩子练的小建议，比如"周末可以和孩子一起跳绳"
5. 最后写一段暖心的话鼓励孩子，比如"XX是个很有活力的孩子，相信坚持下去会越来越棒"

语气要求：
- 像朋友聊天，不要像写公文
- 多用"咱们"、"一起"这样的词
- 适当加入感叹号表达热情
- 避免说"建议您"、"需要改进"这种生硬的话
- 让家长感受到老师是真的关心孩子的成长"""

        latest_record = test_records[0]
        user_prompt = f"""
学生信息：
- 姓名：{student.name}
- 性别：{student.gender}
- 年级：{cls.grade_name if cls else "未知"}

最近测试成绩：
- 测试日期：{latest_record.test_date}
- 总分：{latest_record.total_score}
- 等级：{latest_record.total_grade}
- 详细成绩：{latest_record.grades}

历史测试次数：{len(test_records)}

请生成家长通知书。"""

        # 调用AI生成报告
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        ai_response = deepseek_client.chat(messages)
        
        if ai_response is None:
            raise HTTPException(status_code=500, detail="AI生成失败")
        
        # 创建报告记录
        report = Report(
            report_type="personal",
            student_id=request.student_id,
            content=ai_response,
            comment="AI自动生成，可根据需要修改"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return ReportResponse(
            id=report.id,
            report_type=report.report_type,
            content=report.content,
            comment=report.comment
        )
    
    elif request.report_type == "class":
        # 班级报告
        if not request.class_id:
            raise HTTPException(status_code=400, detail="缺少班级ID")
        
        # 获取班级信息
        cls = db.query(Class).filter(Class.id == request.class_id).first()
        if not cls:
            raise HTTPException(status_code=404, detail="班级不存在")
        
        # 获取班级学生
        students = db.query(Student).filter(Student.class_id == request.class_id).all()
        
        # 统计班级数据
        excellent_count = 0
        good_count = 0
        pass_count = 0
        fail_count = 0
        
        for student in students:
            latest_record = db.query(TestRecord).filter(
                TestRecord.student_id == student.id
            ).order_by(TestRecord.test_date.desc()).first()
            
            if latest_record:
                if latest_record.total_grade == "优秀":
                    excellent_count += 1
                elif latest_record.total_grade == "良好":
                    good_count += 1
                elif latest_record.total_grade == "及格":
                    pass_count += 1
                else:
                    fail_count += 1
        
        # 构建AI提示词
        system_prompt = """你是一位专业的体育教师，擅长撰写班级学情总结报告。

请根据班级数据，生成一份教学总结报告，包含：
1. 班级体质健康整体情况
2. 优良率统计分析
3. 各项目达标对比
4. 班级薄弱项分析
5. 下一步教学重点建议

要求：
- 数据准确、分析客观
- 建议具体、可操作
- 适合提交学校教研总结"""

        user_prompt = f"""
班级信息：
- 班级名称：{cls.name}
- 年级：{cls.grade_name}
- 学生人数：{len(students)}

体质等级分布：
- 优秀：{excellent_count}人（{round(excellent_count/len(students)*100, 1) if students else 0}%）
- 良好：{good_count}人（{round(good_count/len(students)*100, 1) if students else 0}%）
- 及格：{pass_count}人（{round(pass_count/len(students)*100, 1) if students else 0}%）
- 不及格：{fail_count}人（{round(fail_count/len(students)*100, 1) if students else 0}%）

请生成班级学情总结报告。"""

        # 调用AI生成报告
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        ai_response = deepseek_client.chat(messages)
        
        if ai_response is None:
            raise HTTPException(status_code=500, detail="AI生成失败")
        
        # 创建报告记录
        report = Report(
            report_type="class",
            class_id=request.class_id,
            content=ai_response,
            comment="AI自动生成，可根据需要修改"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return ReportResponse(
            id=report.id,
            report_type=report.report_type,
            content=report.content,
            comment=report.comment
        )
    
    else:
        raise HTTPException(status_code=400, detail="不支持的报告类型")

@router.get("/list/{report_type}")
async def list_reports(
    report_type: str,
    student_id: Optional[int] = None,
    class_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取报告列表"""
    if report_type == "personal" and student_id:
        reports = db.query(Report).filter(
            Report.report_type == "personal",
            Report.student_id == student_id
        ).all()
    elif report_type == "class" and class_id:
        reports = db.query(Report).filter(
            Report.report_type == "class",
            Report.class_id == class_id
        ).all()
    else:
        reports = []
    
    return {
        "reports": [
            {
                "id": report.id,
                "report_type": report.report_type,
                "created_at": str(report.created_at)
            }
            for report in reports
        ]
    }

@router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """获取报告详情"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    return {
        "id": report.id,
        "report_type": report.report_type,
        "content": report.content,
        "comment": report.comment,
        "created_at": str(report.created_at)
    }