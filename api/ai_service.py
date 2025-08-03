"""
AI小助手服务模块

提供AI问答服务，结合NO₂数据上下文为用户提供专业、准确的回答。
基于硅基流动API实现。
"""

import os
import requests
from typing import Dict, Any


class AIService:
    """AI服务类，基于硅基流动API"""

    def __init__(self):
        """初始化AI服务配置"""
        self.api_key = os.getenv("AI_API_KEY", "")
        self.api_base = os.getenv("AI_API_BASE", "https://api.siliconflow.cn/v1")
        self.model_name = os.getenv(
            "AI_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"
        )
        self.timeout = 30

    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """构建系统提示词，结合当前城市NO₂数据上下文"""
        city = context.get("city", "未知城市")
        current_value = context.get("currentValue")
        quality_level = context.get("qualityLevel", "未知")
        update_time = context.get("updateTime")
        
        # 构建基础信息
        context_info = f"**{city}城市页面当前数据**：\n"
        if current_value is not None:
            context_info += f"- 当前NO₂浓度：{current_value}μg/m³（{quality_level}）\n"
        if update_time:
            context_info += f"- 数据更新时间：{update_time}\n"
        
        # 添加24小时预测信息
        predictions = context.get("predictions")
        if predictions and predictions.get("values"):
            avg_pred = sum(predictions["values"]) / len(predictions["values"])
            context_info += f"- 未来6小时预测趋势：{predictions['values'][0]:.1f} → {predictions['values'][-1]:.1f}μg/m³\n"
            context_info += f"- 预测置信区间：{predictions['low'][0]:.1f}-{predictions['high'][0]:.1f}μg/m³\n"
        
        # 添加趋势分析信息
        trends = context.get("trends")
        if trends and trends.get("avgValue"):
            context_info += f"- 近15天平均浓度：{trends['avgValue']}\n"
            if trends.get("analysis"):
                context_info += f"- 趋势分析：{trends['analysis'][0] if trends['analysis'] else '暂无'}\n"
        
        # 添加准确性分析信息
        accuracy = context.get("accuracy")
        if accuracy and accuracy.get("mae"):
            context_info += f"- 昨日预测准确性：MAE {accuracy['mae']}，覆盖率 {accuracy['coverage'] or '暂无'}\n"
        
        # 添加防护建议信息
        recommendations = context.get("recommendations")
        if recommendations and recommendations.get("items"):
            context_info += f"- 当前{recommendations['category']}建议：{recommendations['items'][0] if recommendations['items'] else '暂无'}\n"
        
        # 添加页面状态信息
        page_context = context.get("pageContext", {})
        active_section = page_context.get("activeSection", "今日预测结果")
        available_data = page_context.get("availableData", {})
        
        context_info += f"- 用户当前查看：{active_section}部分\n"
        
        # 构建数据可用性说明
        data_status = []
        if available_data.get("hasPredictionData"):
            data_status.append("预测数据")
        if available_data.get("hasTrendData"):
            data_status.append("趋势分析")
        if available_data.get("hasAccuracyData"):
            data_status.append("准确性分析")
        if available_data.get("hasRecommendations"):
            data_status.append("防护建议")
        
        if data_status:
            context_info += f"- 页面可用数据：{', '.join(data_status)}\n"

        # 添加问题分析信息
        question_analysis = context.get("question_analysis")
        if question_analysis:
            intent = question_analysis.get("intent", {})
            context_hints = question_analysis.get("context_hints", [])
            suggested_focus = question_analysis.get("suggested_focus", "")
            
            context_info += f"\n**问题分析**：\n"
            context_info += f"- 问题类型：{intent.get('question_type', '一般咨询')}\n"
            context_info += f"- 建议重点：{suggested_focus}\n"
            if context_hints:
                context_info += f"- 相关数据：{'; '.join(context_hints)}\n"

        return f"""你是专业的NO₂浓度分析AI助手，能够看到用户当前打开的{city}城市详情页面的所有数据。

{context_info}

**核心知识**：
- NO₂标准：优(0-40)、良(40-80)、轻度污染(80-120)、中度污染(120-240)、重度污染(240+) μg/m³
- 主要危害：呼吸道炎症、哮喘加重、肺功能影响
- 防护原则：低浓度正常活动，中等浓度敏感人群注意，高浓度全员防护

**回答要求**：
1. **优先引用页面已显示的具体数据**进行分析
2. 结合用户当前查看的"{active_section}"部分内容
3. 提供基于实际数据的专业解读和建议
4. 语言简洁明了，重点突出，200字以内
5. 如遇非NO₂相关问题，可引导用户关注页面现有的空气质量数据

**特别提醒**：你能看到页面上的所有数据，请充分利用这些信息为用户提供精准、实用的回答。"""

    def analyze_question_intent(self, message: str) -> Dict[str, Any]:
        """分析用户问题意图，确定需要的数据类型"""
        message_lower = message.lower()
        
        intent_analysis = {
            "question_type": "general",
            "needs_prediction": False,
            "needs_trends": False,
            "needs_accuracy": False,
            "needs_recommendations": False,
            "focus_area": "current_status"
        }
        
        # 预测相关问题
        if any(keyword in message_lower for keyword in ["预测", "未来", "预报", "明天", "今晚", "接下来"]):
            intent_analysis.update({
                "question_type": "prediction",
                "needs_prediction": True,
                "focus_area": "future_prediction"
            })
            
        # 趋势分析相关问题  
        elif any(keyword in message_lower for keyword in ["趋势", "变化", "历史", "过去", "最近", "15天", "近期"]):
            intent_analysis.update({
                "question_type": "trends",
                "needs_trends": True,
                "focus_area": "historical_trends"
            })
            
        # 准确性相关问题
        elif any(keyword in message_lower for keyword in ["准确", "精确", "可靠", "误差", "预测准确性", "效果"]):
            intent_analysis.update({
                "question_type": "accuracy",
                "needs_accuracy": True,
                "focus_area": "model_performance"
            })
            
        # 防护建议相关问题
        elif any(keyword in message_lower for keyword in ["防护", "建议", "怎么办", "注意", "措施", "出行", "运动"]):
            intent_analysis.update({
                "question_type": "recommendations",
                "needs_recommendations": True,
                "focus_area": "health_protection"
            })
            
        # 对比分析相关问题
        elif any(keyword in message_lower for keyword in ["对比", "比较", "差异", "相比", "哪个"]):
            intent_analysis.update({
                "question_type": "comparison",
                "needs_prediction": True,
                "needs_trends": True,
                "focus_area": "comparative_analysis"
            })
            
        return intent_analysis

    def enhance_context_dynamically(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """根据问题意图动态增强上下文数据"""
        intent = self.analyze_question_intent(message)
        enhanced_context = context.copy()
        
        # 根据问题类型添加相关的上下文提示
        context_hints = []
        
        if intent["needs_prediction"]:
            predictions = context.get("predictions")
            if predictions and predictions.get("values"):
                context_hints.append(f"预测数据可用：未来6小时浓度变化趋势")
            else:
                context_hints.append("预测数据：页面显示24小时完整预测图表")
                
        if intent["needs_trends"]:
            trends = context.get("trends")
            if trends and trends.get("avgValue"):
                context_hints.append(f"趋势数据可用：15天平均{trends['avgValue']}")
            else:
                context_hints.append("趋势数据：页面包含近15天浓度变化分析")
                
        if intent["needs_accuracy"]:
            accuracy = context.get("accuracy")
            if accuracy and accuracy.get("mae"):
                context_hints.append(f"准确性数据可用：MAE {accuracy['mae']}")
            else:
                context_hints.append("准确性数据：页面显示昨日预测对比分析")
                
        if intent["needs_recommendations"]:
            recommendations = context.get("recommendations")
            if recommendations and recommendations.get("items"):
                context_hints.append(f"防护建议可用：{recommendations['category']}类别")
            else:
                context_hints.append("防护建议：页面提供分类防护建议")
        
        # 将增强信息添加到上下文中
        enhanced_context["question_analysis"] = {
            "intent": intent,
            "context_hints": context_hints,
            "suggested_focus": intent["focus_area"]
        }
        
        return enhanced_context

    def parse_response(self, messages: str) -> str:
        # 请求头
        headers =  {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 请求体
        payload = {
            "model": self.model_name,
            "messages": messages,
        }

        # POST请求
        response = requests.post(
            url=f"{self.api_base}/chat/completions",
            json=payload,
            headers=headers,
            timeout=self.timeout
        )

        # 解析响应
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                raise Exception("API返回格式异常：缺少choices字段")
        elif response.status_code == 401:
            raise Exception("API密钥无效或已过期")
        elif response.status_code == 429:
            raise Exception("API调用频率超限，请稍后重试")
        elif response.status_code == 500:
            raise Exception("硅基流动服务器内部错误")
        else:
            error_detail = ""
            try:
                error_info = response.json()
                error_detail = error_info.get("error", {}).get("message", response.text)
            except:
                error_detail = response.text
            raise Exception(f"API调用失败: {response.status_code}, {error_detail}")

    def get_fallback_response(self, message: str, context: Dict[str, Any]) -> str:
        """当API不可用时的降级回复，利用丰富的页面上下文"""
        message_lower = message.lower()
        city = context.get("city", "该城市")
        current_value = context.get("currentValue")
        quality_level = context.get("qualityLevel", "")
        
        # 获取额外的上下文信息
        predictions = context.get("predictions", {})
        trends = context.get("trends", {})
        accuracy = context.get("accuracy", {})
        recommendations = context.get("recommendations", {})
        page_context = context.get("pageContext", {})
        
        # 构建基础信息
        base_info = f"{city}当前NO₂浓度为{current_value}μg/m³（{quality_level}）"
        
        # 预测趋势相关问题
        if any(keyword in message_lower for keyword in ["趋势", "变化", "预测", "未来"]):
            if predictions and predictions.get("values"):
                current_pred = predictions["values"][0]
                future_pred = predictions["values"][-1]
                trend_desc = "上升" if future_pred > current_pred else "下降" if future_pred < current_pred else "稳定"
                return f"{base_info}。根据页面预测数据，未来6小时浓度将{trend_desc}（{current_pred:.1f} → {future_pred:.1f}μg/m³），建议关注变化趋势合理安排活动。"
            elif trends and trends.get("analysis"):
                return f"{base_info}。{trends['analysis'][0] if trends['analysis'] else '近期趋势数据加载中'}"
            return f"{base_info}。您可以查看页面上的'近15天浓度趋势'图表了解详细变化情况。"

        # 准确性相关问题
        elif any(keyword in message_lower for keyword in ["准确", "精确", "可靠", "预测准确性"]):
            if accuracy and accuracy.get("mae"):
                return f"根据页面显示的准确性分析，昨日预测的平均绝对误差为{accuracy['mae']}，预测区间覆盖率为{accuracy.get('coverage', '计算中')}。{base_info}，模型预测相对可靠。"
            return f"{base_info}。您可以查看页面底部的'昨日预测准确性分析'了解模型表现详情。"

        # 防护建议相关问题
        elif any(keyword in message_lower for keyword in ["防护", "建议", "怎么办", "注意事项"]):
            if recommendations and recommendations.get("items"):
                category_map = {"travel": "出行", "home": "居家", "outdoor": "户外", "exercise": "运动", "special": "特殊人群"}
                category_name = category_map.get(recommendations.get("category", ""), "防护")
                return f"{base_info}。根据页面{category_name}建议：{recommendations['items'][0] if recommendations['items'] else '请查看页面防护建议详情'}。"
            
            # 传统的基于浓度的建议
            if current_value and current_value < 40:
                return f"{base_info}，空气质量优，您可以正常进行户外活动。"
            elif current_value and current_value < 80:
                return f"{base_info}，空气质量良，总体可接受，敏感人群注意防护。"
            elif current_value and current_value < 120:
                return f"{base_info}，轻度污染，敏感人群应减少户外活动时间，外出时建议佩戴口罩。"
            elif current_value and current_value < 240:
                return f"{base_info}，中度污染，建议减少户外活动，关闭门窗，使用空气净化器。"
            else:
                return f"{base_info}，重度污染，避免户外活动，全天关闭门窗，佩戴N95口罩。"

        # 危害影响相关问题
        elif any(keyword in message_lower for keyword in ["危害", "影响", "健康", "伤害"]):
            return f"NO₂对健康的主要危害包括：呼吸道刺激、加重哮喘症状、降低肺功能等。{base_info}，建议您根据页面显示的防护建议采取相应措施。"

        # 浓度数值相关问题
        elif any(keyword in message_lower for keyword in ["浓度", "数值", "水平", "多少"]):
            level_desc = ""
            if current_value:
                if current_value < 40:
                    level_desc = "优，无需特别担心"
                elif current_value < 80:
                    level_desc = "良，总体可接受"
                elif current_value < 120:
                    level_desc = "轻度污染，敏感人群需注意"
                elif current_value < 240:
                    level_desc = "中度污染，需要防护措施"
                else:
                    level_desc = "重度污染，严格防护"
                
                # 添加趋势信息
                if trends and trends.get("avgValue"):
                    return f"{base_info}，{level_desc}。近15天平均浓度为{trends['avgValue']}，可在页面查看详细趋势分析。"
                return f"{base_info}，{level_desc}。"

        # 默认回复
        else:
            active_section = page_context.get("activeSection", "今日预测结果")
            return f"感谢您的提问！{base_info}。您当前正在查看'{active_section}'部分，我可以为您解答关于页面数据的任何疑问，包括NO₂浓度分析、趋势变化、防护建议等。"

    def process_request(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理AI请求的主要方法"""
        try:
            # 检查API密钥配置
            if not self.api_key:
                return {
                    "response": self.get_fallback_response(message, context),
                    "isConnected": False
                }

            # 动态增强上下文
            enhanced_context = self.enhance_context_dynamically(message, context)

            # 构建消息
            system_prompt = self.get_system_prompt(enhanced_context)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]

            # 获取响应
            ai_response = self.parse_response(messages)
            return {
                "response": ai_response,
                "isConnected": True
            }

        except Exception as e:
            print(f"AI API调用失败，使用降级回复: {str(e)}")
            return {
                "response": self.get_fallback_response(message, context),
                "isConnected": False
            }


# 全局AI服务实例
ai_service = AIService()



def get_preset_questions() -> list:
    """获取预设问题列表"""
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
    """验证AI服务配置"""
    return {
        "api_key_configured": bool(os.getenv("AI_API_KEY")),
        "api_base": os.getenv("AI_API_BASE", "https://api.siliconflow.cn/v1"),
        "model_name": os.getenv(
            "AI_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"
        ),
        "fallback_available": True,
    }
