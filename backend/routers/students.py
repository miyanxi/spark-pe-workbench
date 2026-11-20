"""
学生档案管理API路由
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import csv
import io
import os
import re
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Student, Class, Report, TestRecord, TrainingPlan
from scoring_service import ScoringService

router = APIRouter()

# Pydantic模型
class StudentCreate(BaseModel):
    """创建学生请求"""
    class_id: int
    student_id: str
    name: str
    gender: str
    special_conditions: List[str] = Field(default_factory=list)


class StudentImportRow(BaseModel):
    """确认导入时使用的标准学生信息。"""
    student_id: str
    name: str
    gender: str
    special_conditions: List[str] = Field(default_factory=list)


class StudentImportConfirm(BaseModel):
    class_id: int
    rows: List[StudentImportRow]

class TestRecordCreate(BaseModel):
    """创建测试记录请求"""
    student_id: int
    test_date: str
    test_type: str
    scores: dict  # {"50米跑": 9.5, "立定跳远": 2.05, ...}

class StudentResponse(BaseModel):
    """学生响应"""
    id: int
    student_id: str
    name: str
    gender: str
    special_conditions: List[str]
    test_records_count: int
    
    class Config:
        from_attributes = True

@router.post("/create", response_model=StudentResponse)
async def create_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db)
):
    """创建学生"""
    # 检查班级是否存在
    cls = db.query(Class).filter(Class.id == student_data.class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    student_id = student_data.student_id.strip()
    name = student_data.name.strip()
    if not student_id or not name:
        raise HTTPException(status_code=400, detail="学号和姓名不能为空")
    if db.query(Student).filter(
        Student.class_id == student_data.class_id,
        Student.student_id == student_id,
    ).first():
        raise HTTPException(status_code=400, detail="当前班级中已存在该学号")
    
    # 创建学生
    new_student = Student(
        class_id=student_data.class_id,
        student_id=student_id,
        name=name,
        gender=student_data.gender,
        special_conditions=student_data.special_conditions
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    
    return StudentResponse(
        id=new_student.id,
        student_id=new_student.student_id,
        name=new_student.name,
        gender=new_student.gender,
        special_conditions=new_student.special_conditions or [],
        test_records_count=0
    )

HEADER_ALIASES = {
    "student_id": {"学号", "学生编号", "学生学号", "编号", "studentid", "student_id"},
    "name": {"姓名", "学生姓名", "name"},
    "gender": {"性别", "gender"},
    "special_conditions": {
        "特殊健康标记", "特殊体质", "健康标记", "特殊情况", "备注", "specialconditions", "special_conditions"
    },
}


def _normalize_header(value) -> str:
    return re.sub(r"[\s\-（）()]+", "", str(value or "").strip()).lower()


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _normalize_gender(value) -> Optional[str]:
    text = _cell_text(value).lower()
    if text in {"男", "男生", "male", "m", "1"}:
        return "男"
    if text in {"女", "女生", "female", "f", "2"}:
        return "女"
    return None


def _split_conditions(value) -> List[str]:
    text = _cell_text(value)
    if not text or text in {"无", "暂无", "-"}:
        return []
    return [item.strip() for item in re.split(r"[、,，;；/]+", text) if item.strip()]


def _read_import_rows(filename: str, content: bytes):
    extension = os.path.splitext(filename or "")[1].lower()
    if extension == ".xlsx":
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            sheet = workbook.active
            rows = list(sheet.iter_rows(values_only=True))
            workbook.close()
            return rows
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Excel 文件无法读取，请重新下载模板后填写") from exc
    if extension == ".csv":
        decoded = None
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                decoded = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if decoded is None:
            raise HTTPException(status_code=400, detail="CSV 编码无法识别，请另存为 UTF-8 CSV")
        return list(csv.reader(io.StringIO(decoded)))
    raise HTTPException(status_code=400, detail="仅支持 .xlsx 和 .csv 学生名单")


def _map_headers(header_row):
    normalized_aliases = {
        field: {_normalize_header(alias) for alias in aliases}
        for field, aliases in HEADER_ALIASES.items()
    }
    mapping = {}
    for index, value in enumerate(header_row):
        normalized = _normalize_header(value)
        for field, aliases in normalized_aliases.items():
            if normalized in aliases and field not in mapping:
                mapping[field] = index
                break
    missing = [label for field, label in (("student_id", "学号"), ("name", "姓名"), ("gender", "性别")) if field not in mapping]
    if missing:
        raise HTTPException(status_code=400, detail=f"名单缺少必填表头：{'、'.join(missing)}")
    return mapping


@router.get("/import-template")
async def download_import_template():
    """下载带格式和性别下拉选项的 Excel 名单模板。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "学生名单"
    headers = ["学号", "姓名", "性别", "特殊健康标记"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor="0F7B6C")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:D1000"
    sheet.column_dimensions["A"].width = 18
    sheet.column_dimensions["B"].width = 16
    sheet.column_dimensions["C"].width = 10
    sheet.column_dimensions["D"].width = 36
    sheet.row_dimensions[1].height = 24
    gender_validation = DataValidation(type="list", formula1='"男,女"', allow_blank=False)
    gender_validation.error = "请选择男或女"
    gender_validation.errorTitle = "性别格式错误"
    sheet.add_data_validation(gender_validation)
    gender_validation.add("C2:C1000")

    instructions = workbook.create_sheet("填写说明")
    instructions.append(["字段", "填写要求"])
    instructions.append(["学号", "必填；建议设置为文本，避免前导零丢失"])
    instructions.append(["姓名", "必填"])
    instructions.append(["性别", "必填；请选择男或女"])
    instructions.append(["特殊健康标记", "选填；多个标记可用顿号、逗号或分号分隔"])
    instructions.column_dimensions["A"].width = 20
    instructions.column_dimensions["B"].width = 56
    for cell in instructions[1]:
        cell.fill = PatternFill("solid", fgColor="0F7B6C")
        cell.font = Font(color="FFFFFF", bold=True)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=student-import-template.xlsx; filename*=UTF-8''%E5%AD%A6%E7%94%9F%E5%90%8D%E5%8D%95%E5%AF%BC%E5%85%A5%E6%A8%A1%E6%9D%BF.xlsx"
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/batch-import/preview")
async def preview_batch_import(
    class_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """解析名单并返回预览，不在此阶段写入数据库。"""
    if not db.query(Class).filter(Class.id == class_id).first():
        raise HTTPException(status_code=404, detail="班级不存在")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传的名单为空")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="名单文件不能超过 5MB")

    raw_rows = _read_import_rows(file.filename or "", content)
    first_row_index = next((i for i, row in enumerate(raw_rows) if any(_cell_text(v) for v in row)), None)
    if first_row_index is None:
        raise HTTPException(status_code=400, detail="名单中没有可读取的数据")
    mapping = _map_headers(raw_rows[first_row_index])
    existing_ids = {
        row[0] for row in db.query(Student.student_id).filter(Student.class_id == class_id).all()
    }
    seen_ids = set()
    preview_rows = []

    for index, raw_row in enumerate(raw_rows[first_row_index + 1:], start=first_row_index + 2):
        values = list(raw_row)
        if not any(_cell_text(v) for v in values):
            continue
        if len(preview_rows) >= 1000:
            raise HTTPException(status_code=400, detail="单次最多导入 1000 名学生，请拆分名单后再导入")
        get_value = lambda field: values[mapping[field]] if mapping.get(field, -1) < len(values) else None
        student_id = _cell_text(get_value("student_id"))
        name = _cell_text(get_value("name"))
        gender = _normalize_gender(get_value("gender"))
        conditions_value = get_value("special_conditions") if "special_conditions" in mapping else None
        conditions = _split_conditions(conditions_value)
        errors = []
        if not student_id:
            errors.append("缺少学号")
        if not name:
            errors.append("缺少姓名")
        if not gender:
            errors.append("性别必须为男或女")
        if student_id and student_id in existing_ids:
            errors.append("该学号已存在于当前班级")
        if student_id and student_id in seen_ids:
            errors.append("名单内学号重复")
        if student_id:
            seen_ids.add(student_id)
        preview_rows.append({
            "row_number": index,
            "student_id": student_id,
            "name": name,
            "gender": gender or _cell_text(get_value("gender")),
            "special_conditions": conditions,
            "errors": errors,
        })

    if not preview_rows:
        raise HTTPException(status_code=400, detail="表头下方没有学生数据")
    return {
        "filename": file.filename,
        "rows": preview_rows,
        "total_count": len(preview_rows),
        "valid_count": sum(1 for row in preview_rows if not row["errors"]),
        "error_count": sum(1 for row in preview_rows if row["errors"]),
    }


@router.post("/batch-import/confirm")
async def confirm_batch_import(payload: StudentImportConfirm, db: Session = Depends(get_db)):
    """确认并批量写入经过预览的有效学生数据。"""
    if not db.query(Class).filter(Class.id == payload.class_id).first():
        raise HTTPException(status_code=404, detail="班级不存在")
    if not payload.rows:
        raise HTTPException(status_code=400, detail="没有可以导入的学生")
    if len(payload.rows) > 1000:
        raise HTTPException(status_code=400, detail="单次最多导入 1000 名学生")

    existing_ids = {
        row[0] for row in db.query(Student.student_id).filter(Student.class_id == payload.class_id).all()
    }
    seen_ids = set()
    errors = []
    new_students = []
    for index, row in enumerate(payload.rows, start=1):
        student_id = row.student_id.strip()
        name = row.name.strip()
        gender = _normalize_gender(row.gender)
        if not student_id or not name or not gender:
            errors.append(f"第 {index} 条数据缺少学号、姓名或正确性别")
            continue
        if student_id in existing_ids or student_id in seen_ids:
            errors.append(f"学号 {student_id} 已存在或重复")
            continue
        seen_ids.add(student_id)
        new_students.append(Student(
            class_id=payload.class_id,
            student_id=student_id,
            name=name,
            gender=gender,
            special_conditions=[item.strip() for item in row.special_conditions if item.strip()],
        ))
    if errors:
        raise HTTPException(status_code=400, detail="；".join(errors[:10]))

    try:
        db.add_all(new_students)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="名单导入失败，原有数据未被修改")
    return {"message": "学生名单导入成功", "imported_count": len(new_students)}

@router.post("/test-record")
async def create_test_record(
    record_data: TestRecordCreate,
    db: Session = Depends(get_db)
):
    """
    创建测试记录并自动计算得分和等级
    """
    # 获取学生信息
    student = db.query(Student).filter(Student.id == record_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # 获取班级信息
    cls = db.query(Class).filter(Class.id == student.class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    # 计算得分和等级
    scores_dict, avg_score = ScoringService.convert_all_scores(
        record_data.scores,
        cls.grade_name,
        student.gender
    )

    # 解析测试日期
    try:
        test_date = datetime.strptime(record_data.test_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        test_date = datetime.now()

    # 创建测试记录
    test_record = TestRecord(
        student_id=record_data.student_id,
        test_date=test_date,
        test_type=record_data.test_type,
        scores=record_data.scores,
        grades=scores_dict,
        total_score=avg_score,
        total_grade=ScoringService.calculate_total_grade(avg_score)
    )
    db.add(test_record)
    db.commit()
    db.refresh(test_record)
    
    return {
        "message": "测试记录创建成功",
        "test_record_id": test_record.id,
        "total_score": test_record.total_score,
        "total_grade": test_record.total_grade,
        "details": scores_dict
    }

@router.post("/ocr-import")
async def ocr_import_test_records(
    class_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    OCR识别成绩单并导入
    
    TODO: 需要调用视觉模型API进行识别
    
    注意：调用AI模型前需要向用户确认模型是否能用
    """
    # TODO: 
    # 1. 上传图片到临时目录
    # 2. 调用后续选定的 OCR / 视觉模型识别
    # 3. 解析结构化数据
    # 4. 批量创建测试记录
    
    return {"message": "OCR识别功能待实现（需要确认模型是否可用）"}

@router.get("/list/{class_id}", response_model=List[StudentResponse])
async def list_students(class_id: int, db: Session = Depends(get_db)):
    """获取班级学生列表"""
    students = db.query(Student).filter(Student.class_id == class_id).all()
    
    result = []
    for student in students:
        test_records_count = db.query(TestRecord).filter(TestRecord.student_id == student.id).count()
        result.append(StudentResponse(
            id=student.id,
            student_id=student.student_id,
            name=student.name,
            gender=student.gender,
            special_conditions=student.special_conditions or [],
            test_records_count=test_records_count
        ))
    
    return result

@router.get("/{student_id}")
async def get_student(student_id: int, db: Session = Depends(get_db)):
    """获取学生详情"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # 获取测试记录
    test_records = db.query(TestRecord).filter(TestRecord.student_id == student_id).all()
    
    return {
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "gender": student.gender,
            "special_conditions": student.special_conditions
        },
        "test_records": [
            {
                "id": record.id,
                "test_date": record.test_date,
                "test_type": record.test_type,
                "scores": record.scores,
                "grades": record.grades,
                "total_score": record.total_score,
                "total_grade": record.total_grade
            }
            for record in test_records
        ]
    }


@router.delete("/{student_id}")
async def delete_student(student_id: int, db: Session = Depends(get_db)):
    """删除学生及其全部成绩、训练方案和个人报告。"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    student_name = student.name
    try:
        db.query(Report).filter(Report.student_id == student_id).delete(synchronize_session=False)
        db.query(TrainingPlan).filter(TrainingPlan.student_id == student_id).delete(synchronize_session=False)
        db.query(TestRecord).filter(TestRecord.student_id == student_id).delete(synchronize_session=False)
        db.delete(student)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="学生删除失败，原有数据未被修改")

    return {"message": "学生已删除", "student_id": student_id, "student_name": student_name}
