"""
agents.py
Phase 2.5 完整四态情绪状态机 (4-State Emotional FSM)
包含：Neutral, Skeptical, Aggressive, Encouraging 状态库，及其马尔可夫转移矩阵。
"""

from typing import List, Dict

# 基础系统背景定义 (超精简 Logic-First 模式)
# 基础系统背景定义 (S²-MAD 2025: Surgical Logic Compression)
BASE_SYS_PROMPT = """You are a high-speed logic reasoning node.
Mandatory Format:
<Rationale>
[Atomic Logic Steps Only]. Max 60 words. Forbidden: repeating task, filler text, meta-commentary.
</Rationale>
<Response>
Final deduction or target challenge.
</Response>

Core Constraint: Each token must represent a logical pivot. Brevity is the highest priority."""

# 四种态势的子 Prompt (剥离情绪形容词，保留逻辑动作)
EMOTIONS = {
    "Neutral": """
State: Analytical.
Instruction: Deconstruct the problem using formal logic. 
""",
    "Skeptical": """
State: Critical.
Instruction: Find the single biggest contradiction or missing link in the other agent's claim. Target it directly.
""",
    "Aggressive": """
State: Disruptive.
Instruction: The other agent is fundamentally wrong. Dismantle their entire causal chain. Force a reset of their logic.
""",
    "Encouraging": """
State: Guided.
Instruction: Simplified logic. Guide the discussion back to the core premises.
"""
}

class StatefulAgent:
    def __init__(self, name: str, initial_state: str = "Neutral"):
        self.name = name
        self.state = initial_state
        self.history: List[str] = []  # 记录收到的回应（简化用于状态转移）
        
        # 记录特定行为发生的次数，以匹配基于轮次/频次的转移条件
        self.rebuttals_received = 0
        self.lazy_replies_received = 0
        
    def build_current_prompt(self) -> str:
        """根据当前状态拼合生成系统提示词"""
        return f"{BASE_SYS_PROMPT}\n\n{EMOTIONS.get(self.state, EMOTIONS['Neutral'])}"
        
    def transition_state(self, incoming_message: str, is_lazy: bool = False, curator_force: str = None) -> str:
        """
        基于新收到的消息和外部特征执行马尔可夫状态提取与转移。
        """
        if curator_force:
            # 外部 Curator 信号拥有最高优先级
            self.state = curator_force
            return self.state
            
        msg_lower = incoming_message.lower()
        
        # 特征提取
        is_confused = any(ph in msg_lower for ph in ["我不太确定", "太复杂了", "我不确定", "也许你对", "可能你是对的"])
        is_rebuttal = not is_lazy and not is_confused and ("不认同" in msg_lower or "你错了" in msg_lower or "这不成立" in msg_lower)
        
        if is_lazy:
            self.lazy_replies_received += 1
        else:
            self.lazy_replies_received = max(0, self.lazy_replies_received - 1)
            
        if is_rebuttal:
            self.rebuttals_received += 1
            
        # 马尔可夫状态转移规则
        previous_state = self.state
        
        if self.state == "Neutral":
            if is_confused:
                self.state = "Encouraging"
            elif self.rebuttals_received >= 1:
                self.state = "Skeptical"
                
        elif self.state == "Skeptical":
            if self.lazy_replies_received >= 2:
                self.state = "Aggressive"
                
        elif self.state == "Aggressive":
            # 如果处于强制打破僵局的攻击态，对方给出了高质量长推理，回归理性
            if not is_lazy and not is_confused and len(msg_lower) > 50:
                self.state = "Skeptical"
                
        # Encouraging 的退出条件：如果对方振作起来开始反驳，切回 Neutral 或 Skeptical
        elif self.state == "Encouraging":
            if is_rebuttal:
                self.state = "Neutral"

        print(f"🔄 [FSM Transition] {self.name}: {previous_state} -> {self.state}")
        return self.state
