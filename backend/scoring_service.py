"""
国标换算服务 - 基于《国家学生体质健康标准（2014年修订）》
"""
import json
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BASE_DIR

# 加载国标评分标准
STANDARD_FILE = os.path.join(BASE_DIR, "national_fitness_standard.json")

with open(STANDARD_FILE, 'r', encoding='utf-8') as f:
    STANDARD_DATA = json.load(f)


class ScoringService:
    """评分服务"""

    # ---- 通用辅助 ----

    @staticmethod
    def _norm_gender(gender):
        """将性别统一为英文 male/female"""
        g = str(gender).strip().lower()
        if g in ("男", "male", "m", "1"):
            return "male"
        return "female"

    @staticmethod
    def _get_grade_index(table_key, grade_name):
        """获取年级在评分表中的索引"""
        grades = STANDARD_DATA["scoring_tables"][table_key]["grades"]
        if grade_name not in grades:
            return None
        return grades.index(grade_name)

    @staticmethod
    def calculate_total_grade(total_score):
        """计算总等级"""
        if total_score >= 90:
            return "优秀"
        elif total_score >= 80:
            return "良好"
        elif total_score >= 60:
            return "及格"
        else:
            return "不及格"

    # ---- 越大越好型（肺活量、立定跳远、坐位体前屈、引体向上、仰卧起坐、跳绳）----

    @staticmethod
    def _score_higher_better(value, table_key, grade_name):
        """值越大得分越高"""
        idx = ScoringService._get_grade_index(table_key, grade_name)
        if idx is None:
            return None
        s = STANDARD_DATA["scoring_tables"][table_key]["scores"]
        v = float(value)
        if v >= s["100"][idx]:
            return 100.0
        elif v >= s["90"][idx]:
            return round(90 + (v - s["90"][idx]) / (s["100"][idx] - s["90"][idx]) * 10, 1)
        elif v >= s["80"][idx]:
            return round(80 + (v - s["80"][idx]) / (s["90"][idx] - s["80"][idx]) * 10, 1)
        elif v >= s["60"][idx]:
            return round(60 + (v - s["60"][idx]) / (s["80"][idx] - s["60"][idx]) * 20, 1)
        else:
            return round(max(10, 60 * v / s["60"][idx]), 1) if s["60"][idx] > 0 else 10

    # ---- 越小越好型（50米跑、耐力跑）----

    @staticmethod
    def _score_lower_better(value, table_key, grade_name):
        """值越小得分越高（如跑步用时）"""
        idx = ScoringService._get_grade_index(table_key, grade_name)
        if idx is None:
            return None
        s = STANDARD_DATA["scoring_tables"][table_key]["scores"]
        v = float(value)
        if v <= s["100"][idx]:
            return 100.0
        elif v <= s["90"][idx]:
            return round(90 + (s["90"][idx] - v) / (s["90"][idx] - s["100"][idx]) * 10, 1)
        elif v <= s["80"][idx]:
            return round(80 + (s["80"][idx] - v) / (s["80"][idx] - s["90"][idx]) * 10, 1)
        elif v <= s["60"][idx]:
            return round(60 + (s["60"][idx] - v) / (s["60"][idx] - s["80"][idx]) * 20, 1)
        else:
            return round(max(10, 60 * s["60"][idx] / v), 1) if v > 0 else 10

    # ---- 各项目评分 ----

    @staticmethod
    def calculate_bmi_score(bmi, grade_name, gender):
        """计算BMI得分"""
        key = f"BMI_{ScoringService._norm_gender(gender)}"
        if key not in STANDARD_DATA["scoring_tables"]:
            return None, None
        idx = ScoringService._get_grade_index(key, grade_name)
        if idx is None:
            return None, None
        scores = STANDARD_DATA["scoring_tables"][key]["scores"]
        bmi = float(bmi)

        normal_range = scores["100"]["ranges"][idx]
        low_range = scores["80"]["ranges"][idx]
        overweight_range = scores["80_overweight"]["ranges"][idx]
        obese_range = scores["60"]["ranges"][idx]

        normal_min, normal_max = map(float, normal_range.split("~"))
        ow_min, ow_max = map(float, overweight_range.split("~"))
        low_max = float(low_range.replace("≤", ""))
        obese_min = float(obese_range.replace("≥", ""))

        if normal_min <= bmi <= normal_max:
            return 100, "正常"
        elif bmi < low_max:
            return 80, "低体重"
        elif ow_min <= bmi <= ow_max:
            return 80, "超重"
        elif bmi >= obese_min:
            return 60, "肥胖"
        return 80, "正常"

    @staticmethod
    def calculate_vital_capacity_score(value, grade_name, gender):
        return ScoringService._score_higher_better(value, f"vital_capacity_{ScoringService._norm_gender(gender)}", grade_name)

    @staticmethod
    def calculate_50m_run_score(seconds, grade_name, gender):
        return ScoringService._score_lower_better(seconds, f"50m_run_{ScoringService._norm_gender(gender)}", grade_name)

    @staticmethod
    def calculate_sit_and_reach_score(value, grade_name, gender):
        return ScoringService._score_higher_better(value, f"sit_and_reach_{ScoringService._norm_gender(gender)}", grade_name)

    @staticmethod
    def calculate_standing_long_jump_score(value, grade_name, gender):
        return ScoringService._score_higher_better(value, f"standing_long_jump_{ScoringService._norm_gender(gender)}", grade_name)

    @staticmethod
    def calculate_pull_ups_score(value, grade_name, gender="男"):
        return ScoringService._score_higher_better(value, "pull_ups_male", grade_name)

    @staticmethod
    def calculate_sit_ups_junior_score(value, grade_name, gender="女"):
        return ScoringService._score_higher_better(value, "sit_ups_female", grade_name)

    @staticmethod
    def calculate_rope_skip_score(value, grade_name):
        """小学跳绳"""
        return ScoringService._score_higher_better(value, "rope_skip_primary", grade_name)

    @staticmethod
    def calculate_sit_ups_primary_score(value, grade_name):
        """小学仰卧起坐"""
        return ScoringService._score_higher_better(value, "sit_ups_primary", grade_name)

    @staticmethod
    def calculate_1000m_run_score(seconds, grade_name, gender="男"):
        if ScoringService._norm_gender(gender) == "male":
            return ScoringService._score_lower_better(seconds, "1000m_run_male", grade_name)
        else:
            return ScoringService._score_lower_better(seconds, "800m_run_female", grade_name)

    @staticmethod
    def convert_all_scores(scores_dict, grade_name, gender):
        """
        转换所有成绩为得分和等级

        Args:
            scores_dict: 成绩字典，支持中文或英文键名
            grade_name: 年级名称（如"三年级"、"初一"）
            gender: 性别（"男"/"女"）

        Returns:
            (grades_dict, avg_score)
        """
        # 键名映射：英文 -> 中文
        key_map = {
            "height": "身高",
            "weight": "体重",
            "vital_capacity": "肺活量",
            "50m_run": "50米跑",
            "sit_and_reach": "坐位体前屈",
            "standing_long_jump": "立定跳远",
            "1min_rope_skip": "1分钟跳绳",
            "1min_sit_ups": "1分钟仰卧起坐",
            "1000m_run": "1000米跑",
            "800m_run": "800米跑",
            "pull_ups": "引体向上",
        }

        result = {}
        score_list = []
        height = None
        weight = None

        for raw_key, value in scores_dict.items():
            cn_key = key_map.get(raw_key, raw_key)

            if cn_key == "身高":
                height = float(value)
                result[cn_key] = {"raw_value": value, "score": None, "grade": "-"}
                continue
            if cn_key == "体重":
                weight = float(value)
                result[cn_key] = {"raw_value": value, "score": None, "grade": "-"}
                continue

            score = None

            # BMI 需要身高+体重
            if cn_key in ("BMI",) or (height and weight and cn_key == "BMI"):
                bmi = weight / (height / 100) ** 2 if height else None
                if bmi:
                    s, g = ScoringService.calculate_bmi_score(bmi, grade_name, gender)
                    result["BMI"] = {"raw_value": round(bmi, 1), "score": s, "grade": g}
                    if s:
                        score_list.append(s)
                continue

            if cn_key == "肺活量":
                score = ScoringService.calculate_vital_capacity_score(value, grade_name, gender)
            elif cn_key == "50米跑":
                score = ScoringService.calculate_50m_run_score(value, grade_name, gender)
            elif cn_key == "坐位体前屈":
                score = ScoringService.calculate_sit_and_reach_score(value, grade_name, gender)
            elif cn_key == "立定跳远":
                score = ScoringService.calculate_standing_long_jump_score(value, grade_name, gender)
            elif cn_key == "引体向上":
                score = ScoringService.calculate_pull_ups_score(value, grade_name, gender)
            elif cn_key == "1分钟仰卧起坐":
                # 小学用小学表，初中高中用女生表
                gm = STANDARD_DATA["grade_mapping"].get(grade_name, {})
                if gm.get("level") == "primary":
                    score = ScoringService.calculate_sit_ups_primary_score(value, grade_name)
                else:
                    score = ScoringService.calculate_sit_ups_junior_score(value, grade_name, gender)
            elif cn_key == "1分钟跳绳":
                score = ScoringService.calculate_rope_skip_score(value, grade_name)
            elif cn_key in ("1000米跑", "800米跑"):
                # 男生1000米，女生800米 —— 统一按性别评分
                score = ScoringService.calculate_1000m_run_score(value, grade_name, gender)

            if score is not None:
                result[cn_key] = {
                    "raw_value": value,
                    "score": score,
                    "grade": ScoringService.calculate_total_grade(score)
                }
                score_list.append(score)
            else:
                result[cn_key] = {"raw_value": value, "score": None, "grade": "-"}

        # 计算BMI（如果身高体重都有）
        if height and weight and "BMI" not in result:
            bmi = round(weight / (height / 100) ** 2, 1)
            s, g = ScoringService.calculate_bmi_score(bmi, grade_name, gender)
            result["BMI"] = {"raw_value": bmi, "score": s, "grade": g}
            if s:
                score_list.append(s)

        avg_score = round(sum(score_list) / len(score_list), 1) if score_list else 0
        return result, avg_score
