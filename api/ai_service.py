"""
AI小助手服务模块

提供AI问答服务，结合NO₂数据上下文为用户提供专业、准确的回答。
支持多种大模型API，包括OpenAI、国产大模型等。
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class AIService:
    """AI服务类，处理与大模型API的交互"""
    
    def __init__(self):
        """初始化AI服务配置"""
        # 从环境变量获取API配置
        self.api_key = os.getenv("AI_API_KEY", "")
        self.api_base = os.getenv("AI_API_BASE", "https://api.openai.com/v1")
        self.model_name = os.getenv("AI_MODEL_NAME", "gpt-3.5-turbo")
        self.timeout = 30
        
        # NO₂相关的专业知识库
        self.no2_knowledge = {
            "基础知识": {
                "什么是NO₂": "NO₂（二氧化氮）是一种重要的大气污染物，主要来源于机动车尾气、工业排放和燃煤等。",
                "危害": "NO₂可引起呼吸道炎症，增加哮喘和呼吸道感染风险，长期暴露可能导致肺功能下降。",
                "标准": "中国环境空气质量标准中，NO₂的1小时平均浓度限值为200μg/m³，年平均浓度限值为40μg/m³。"
            },
            "浓度等级": {
                "优": "0-40μg/m³，空气质量令人满意，基本无空气污染",
                "良": "40-80μg/m³，空气质量可以接受，对敏感人群有轻微影响",
                "轻度污染": "80-120μg/m³，敏感人群症状有轻度加剧",
                "中度污染": "120-240μg/m³，进一步加剧易感人群症状",
                "重度污染": "240μg/m³以上，健康人群也会出现症状"
            },
            "防护建议": {
                "低浓度": "正常户外活动，保持室内通风",
                "中等浓度": "敏感人群减少户外活动，外出佩戴口罩",
                "高浓度": "避免户外活动，关闭门窗，使用空气净化器"
            }
        }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建系统提示词，结合当前城市NO₂数据上下文
        
        Args:
            context: 上下文数据，包含城市、浓度值等信息
            
        Returns:
            str: 系统提示词
        """
        city = context.get("city", "未知城市")
        current_value = context.get("currentValue")
        avg_value = context.get("avgValue")
        quality_level = context.get("qualityLevel", "未知")
        
        # 构建上下文信息
        context_info = f"当前查询城市：{city}\n"
        if current_value is not None:
            context_info += f"当前NO₂浓度：{current_value}μg/m³\n"
        if avg_value is not None:
            context_info += f"24小时平均浓度：{avg_value}μg/m³\n"
        context_info += f"空气质量等级：{quality_level}\n"
        
        system_prompt = f"""你是一个专业的NO₂浓度分析AI助手，具备以下特点：

1. **专业背景**：你精通空气质量、环境科学和公共健康知识
2. **数据驱动**：你的回答基于科学数据和环境标准
3. **实用性强**：你提供具体、可操作的建议
4. **用户友好**：你用通俗易懂的语言解释复杂概念

**当前数据上下文**：
{context_info}

**核心知识**：
- NO₂标准：优(0-40)、良(40-80)、轻度污染(80-120)、中度污染(120-240)、重度污染(240+) μg/m³
- 主要危害：呼吸道炎症、哮喘加重、肺功能影响
- 防护原则：低浓度正常活动，中等浓度敏感人群注意，高浓度全员防护

**回答要求**：
1. 结合当前城市的实际数据进行分析
2. 提供具体的数值解读和健康建议
3. 语言简洁明了，避免过于技术化的表述
4. 回答长度控制在200字以内
5. 如果问题与NO₂无关，温和地引导用户关注空气质量话题

请根据用户问题和上述上下文，提供专业而实用的回答。"""
        
        return system_prompt
    
    def call_openai_api(self, messages: list) -> str:
        """
        调用OpenAI API获取回复
        
        Args:
            messages: 消息列表
            
        Returns:
            str: AI回复内容
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=data,
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"API调用失败: {response.status_code}, {response.text}")
    
    def get_fallback_response(self, message: str, context: Dict[str, Any]) -> str:
        """
        当API不可用时的降级回复
        
        Args:
            message: 用户消息
            context: 上下文数据
            
        Returns:
            str: 降级回复内容
        """
        message_lower = message.lower()
        city = context.get("city", "该城市")
        current_value = context.get("currentValue")
        quality_level = context.get("qualityLevel", "")
        
        # 预设回复模板
        if any(keyword in message_lower for keyword in ["危害", "影响", "健康"]):
            return f"NO₂对健康的主要危害包括：呼吸道刺激、加重哮喘症状、降低肺功能等。{city}当前NO₂浓度为{current_value}μg/m³（{quality_level}），建议您根据浓度水平采取相应防护措施。"
        
        elif any(keyword in message_lower for keyword in ["防护", "建议", "怎么办"]):
            if current_value and current_value < 40:
                return f"{city}当前NO₂浓度为{current_value}μg/m³，空气质量优良，您可以正常进行户外活动，建议保持室内适当通风。"
            elif current_value and current_value < 120:
                return f"{city}当前NO₂浓度为{current_value}μg/m³，敏感人群应减少户外活动时间，外出时建议佩戴口罩。"
            else:
                return f"{city}当前NO₂浓度较高，建议减少户外活动，关闭门窗，使用空气净化器，敏感人群尤其要注意防护。"
        
        elif any(keyword in message_lower for keyword in ["浓度", "数值", "水平"]):
            if current_value:
                level_desc = ""
                if current_value < 40:
                    level_desc = "优秀，无需特别担心"
                elif current_value < 80:
                    level_desc = "良好，总体可接受"
                elif current_value < 120:
                    level_desc = "轻度污染，敏感人群需注意"
                else:
                    level_desc = "污染较重，需要防护措施"
                
                return f"{city}当前NO₂浓度为{current_value}μg/m³，空气质量等级为{quality_level}，{level_desc}。建议您关注空气质量变化，合理安排户外活动。"
        
        elif any(keyword in message_lower for keyword in ["趋势", "变化", "预测"]):
            return f"基于{city}的历史数据和气象条件，NO₂浓度会受到交通流量、工业排放、气象条件等因素影响。建议您定期查看我们的预测数据，合理规划出行。"
        
        elif any(keyword in message_lower for keyword in ["运动", "锻炼", "健身"]):
            if current_value and current_value < 80:
                return f"{city}当前NO₂浓度为{current_value}μg/m³，适合进行户外运动，建议选择空气流通较好的公园或郊外。"
            else:
                return f"{city}当前NO₂浓度为{current_value}μg/m³，建议选择室内运动，或等待空气质量改善后再进行户外锻炼。"
        
        else:
            return f"感谢您的提问！{city}当前NO₂浓度为{current_value}μg/m³（{quality_level}）。我可以为您解答关于NO₂浓度、健康影响、防护建议等相关问题。您还想了解什么呢？"
    
    def process_request(self, message: str, context: Dict[str, Any]) -> str:
        """
        处理AI请求的主要方法
        
        Args:
            message: 用户消息
            context: 上下文数据
            
        Returns:
            str: AI回复内容
        """
        try:
            # 检查API密钥配置
            if not self.api_key:
                print("警告：未配置AI_API_KEY，使用降级回复")
                return self.get_fallback_response(message, context)
            
            # 构建消息
            system_prompt = self.get_system_prompt(context)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            # 调用API
            response = self.call_openai_api(messages)
            return response
            
        except Exception as e:
            print(f"AI API调用失败，使用降级回复: {str(e)}")
            return self.get_fallback_response(message, context)


# 全局AI服务实例
ai_service = AIService()


def process_ai_request(message: str, context: Dict[str, Any]) -> str:
    """
    处理AI请求的入口函数
    
    Args:
        message: 用户消息
        context: 上下文数据，包含城市、NO₂浓度等信息
        
    Returns:
        str: AI回复内容
        
    Example:
        >>> context = {
        ...     "city": "广州",
        ...     "currentValue": 25.6,
        ...     "avgValue": 23.4,
        ...     "qualityLevel": "良"
        ... }
        >>> response = process_ai_request("NO₂的危害有哪些？", context)
        >>> print(response)
    """
    return ai_service.process_request(message, context)


def get_preset_questions() -> list:
    """
    获取预设问题列表
    
    Returns:
        list: 预设问题列表
    """
    return [
        "NO₂的危害有哪些？",
        "当前城市的NO₂浓度水平如何？",
        "近期NO₂浓度变化趋势怎样？",
        "高NO₂浓度时应该如何防护？",
        "NO₂浓度对运动有什么影响？",
        "敏感人群如何应对NO₂污染？",
        "室内如何减少NO₂的影响？",
        "NO₂浓度的评价标准是什么？"
    ]


def validate_ai_config() -> Dict[str, Any]:
    """
    验证AI服务配置
    
    Returns:
        dict: 配置验证结果
    """
    config_status = {
        "api_key_configured": bool(os.getenv("AI_API_KEY")),
        "api_base": os.getenv("AI_API_BASE", "https://api.openai.com/v1"),
        "model_name": os.getenv("AI_MODEL_NAME", "gpt-3.5-turbo"),
        "fallback_available": True
    }
    
    return config_status