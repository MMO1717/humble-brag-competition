from pydantic import BaseModel
from enum import Enum
from typing import Optional, List

class PlatformEnum(Enum):
    """
    社交平台枚举
    """
    WECHAT_MOMENTS = "微信朋友圈"
    WEIBO = "微博"
    XIAOHONGSHU = "小红书"
    TIKTOK = "抖音"
    KUAISHOU = "快手"
    LINKEDIN = "LinkedIn"
    TWITTER = "Twitter"
    FACEBOOK = "Facebook"
    INSTAGRAM = "Instagram"

class RelationshipEnum(Enum):
    """
    关系类型枚举
    """
    FAMILY = "家人"
    SPOUSE = "配偶"
    CHILDREN = "子女"
    PARENTS = "父母"
    FRIEND = "好友"
    COLLEAGUE = "同事"
    BOSS = "老板"
    SUBORDINATE = "下属"
    ACQUAINTANCE = "熟人"
    STRANGER = "陌生人"
    CLIENT = "客户"
    PARTNER = "合作伙伴"
    COMPETITOR = "竞争对手"

class AgentRoleEnum(Enum):
    """
    代理角色枚举
    """
    FAMILY_MEMBER = "家庭成员"
    SPOUSE = "配偶"
    PARENT = "家长"
    CHILD = "孩子"
    FRIEND = "普通朋友"
    BEST_FRIEND = "挚友"
    COLLEAGUE = "同事"
    BOSS = "老板"
    SUBORDINATE = "下属"
    MENTOR = "导师"
    STUDENT = "学生"
    CLIENT = "客户"
    SERVICE_PROVIDER = "服务提供者"
    NEIGHBOR = "邻居"
    ACQUAINTANCE = "熟人"

class InteractionGoalEnum(Enum):
    """
    互动目标枚举
    """
    FAVORABLE_RESPONSE = "友好回应"
    EMPATHETIC_SUPPORT = "情感支持"
    INFORMATION_SHARING = "信息分享"
    PROMOTION = "推广产品/服务"
    RELATIONSHIP_BUILDING = "建立关系"
    NETWORK_EXPANSION = "扩展网络"
    INFLUENCE_OPINION = "影响观点"
    MAINTAIN_DISTANCE = "保持距离"
    AVOID_CONFLICT = "避免冲突"
    SEEK_HELP = "寻求帮助"
    PROVIDE_HELP = "提供帮助"
    ENTERTAINMENT = "娱乐互动"

class PostTypeEnum(Enum):
    """
    帖子类型枚举
    """
    STATUS_UPDATE = "状态更新"
    ACHIEVEMENT = "成就分享"
    COMPLAINT = "抱怨"
    QUESTION = "提问"
    ADVICE_SEEKING = "寻求建议"
    INFORMATION_SHARING = "信息分享"
    EMOTIONAL_OUTBURST = "情绪宣泄"
    PRODUCT_PROMOTION = "产品推广"
    EVENT_ANNOUNCEMENT = "活动公告"
    LIFE_MOMENT = "生活瞬间"

class SocialContext(BaseModel):
    """
    社交上下文模型 - 包含所有必要的社交信息
    """
    platform: PlatformEnum
    relationship: RelationshipEnum
    agent_role: AgentRoleEnum
    interaction_goal: InteractionGoalEnum
    post_content: str
    post_type: Optional[PostTypeEnum] = None
    sender_name: Optional[str] = None
    timestamp: Optional[str] = None
    engagement_metrics: Optional[dict] = None  # 点赞、评论数等

    def to_metastring(self) -> str:
        """
        将社交上下文转换为 Meta-String 格式
        """
        metastore = f"[Platform: {self.platform.value}] [Relationship: {self.relationship.value}] [Agent_Role: {self.agent_role.value}] [Interaction_Goal: {self.interaction_goal.value}] [Post: {self.post_content}]"

        if self.post_type:
            metastore += f" [Post_Type: {self.post_type.value}]"
        if self.sender_name:
            metastore += f" [Sender_Name: {self.sender_name}]"
        if self.timestamp:
            metastore += f" [Timestamp: {self.timestamp}]"

        return metastore

    @classmethod
    def from_metastring(cls, metastring: str):
        """
        从 Meta-String 解析出社交上下文
        """
        # 简单解析 metastore 字符串
        import re

        # 提取不同字段
        platform_match = re.search(r'\[Platform: ([^\]]+)\]', metastring)
        relationship_match = re.search(r'\[Relationship: ([^\]]+)\]', metastring)
        agent_role_match = re.search(r'\[Agent_Role: ([^\]]+)\]', metastring)
        interaction_goal_match = re.search(r'\[Interaction_Goal: ([^\]]+)\]', metastring)
        post_match = re.search(r'\[Post: ([^\]]+)\]', metastring)
        post_type_match = re.search(r'\[Post_Type: ([^\]]+)\]', metastring)
        sender_name_match = re.search(r'\[Sender_Name: ([^\]]+)\]', metastring)
        timestamp_match = re.search(r'\[Timestamp: ([^\]]+)\]', metastring)

        # 匹配枚举值
        platform = None
        for p in PlatformEnum:
            if p.value == platform_match.group(1) if platform_match else None:
                platform = p
                break

        relationship = None
        for r in RelationshipEnum:
            if r.value == relationship_match.group(1) if relationship_match else None:
                relationship = r
                break

        agent_role = None
        for ar in AgentRoleEnum:
            if ar.value == agent_role_match.group(1) if agent_role_match else None:
                agent_role = ar
                break

        interaction_goal = None
        for ig in InteractionGoalEnum:
            if ig.value == interaction_goal_match.group(1) if interaction_goal_match else None:
                interaction_goal = ig
                break

        post_type = None
        for pt in PostTypeEnum:
            if pt.value == post_type_match.group(1) if post_type_match else None:
                post_type = pt
                break

        return cls(
            platform=platform,
            relationship=relationship,
            agent_role=agent_role,
            interaction_goal=interaction_goal,
            post_content=post_match.group(1) if post_match else "",
            post_type=post_type,
            sender_name=sender_name_match.group(1) if sender_name_match else None,
            timestamp=timestamp_match.group(1) if timestamp_match else None
        )

class ResponseStrategy(BaseModel):
    """
    回复策略模型
    """
    tone: str  # 语调：正式、随意、幽默、同情等
    content_type: str  # 内容类型：文字、表情、图片链接等
    engagement_level: str  # 参与程度：高、中、低
    personalization_level: str  # 个性化程度：高度个性化、一般、标准化
    suggested_response: str  # 建议的回复内容
    confidence_score: float  # 置信度分数 0-1