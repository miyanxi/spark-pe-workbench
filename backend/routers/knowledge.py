"""
知识库问答API路由
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepseek_client import deepseek_client

router = APIRouter()

class QuestionRequest(BaseModel):
    """提问请求"""
    question: str
    grade_level: Optional[str] = None  # 学段：primary/junior/senior
    grade_name: Optional[str] = None   # 具体年级

class AnswerResponse(BaseModel):
    """回答响应"""
    question: str
    answer: str
    grade_level: Optional[str]
    grade_name: Optional[str]

@router.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    知识库问答
    
    支持文字输入，根据学段自适应回答
    """
    # 构建系统提示词
    system_prompt = """你是一位专业的体育教学助手，拥有丰富的体育教学知识。

你的回答应该：
1. 结构化呈现：动作要领 → 练习方法 → 常见易错点与纠正 → 保护与帮助
2. 简洁明了：避免冗长段落，每个部分用要点列表呈现
3. 专业准确：确保技术动作描述准确，符合教学规范
4. 安全提醒：涉及高危或易受损伤的动作时，在回答顶部置顶"安全风险防范卡"

请根据问题中的学段信息，调整回答的难度和内容深度：
- 小学：趣味性强、简单易学、游戏化
- 初中：进阶强化、技术提升、分层练习
- 高中：专项提升、战术配合、高强度训练"""

    # 构建用户提示词
    user_prompt = request.question
    if request.grade_name:
        user_prompt = f"{request.grade_name} {user_prompt}"
    
    # 调用 DeepSeek 官方 API
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    answer = deepseek_client.chat(messages)
    
    if answer is None:
        answer = "抱歉，系统暂时无法回答您的问题，请稍后再试。"
    
    return AnswerResponse(
        question=request.question,
        answer=answer,
        grade_level=request.grade_level,
        grade_name=request.grade_name
    )

@router.get("/categories")
async def get_categories():
    """获取知识库分类"""
    return {
        "categories": [
            {
                "name": "体测项目",
                "subcategories": ["50米跑", "立定跳远", "坐位体前屈", "跳绳", "耐力跑", "力量练习"]
            },
            {
                "name": "专项技能",
                "subcategories": ["篮球", "足球", "排球", "乒乓球", "羽毛球", "武术", "体操"]
            },
            {
                "name": "运动理论",
                "subcategories": ["运动生理", "运动损伤预防", "运动营养", "运动心理学"]
            },
            {
                "name": "安全急救",
                "subcategories": ["常见损伤处理", "急救知识", "防护措施", "应急处理"]
            }
        ]
    }
