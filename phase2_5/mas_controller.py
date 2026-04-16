"""
mas_controller.py
Phase 2.5 多智能体控制图心跳 (Qwen / DashScope 版本)
引入 Node Dropout（动态节点剔除机制）和完整的 4 态 FSM 调用。
使用 OpenAI 兼容模式调用自研中转或通义千问端点。
"""

import asyncio
from openai import AsyncOpenAI
from agents import StatefulAgent
from curator import check_physio_lazy_agreement

class MAS_Controller:
    def __init__(self, api_key: str, model_id: str, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        # 切换至 OpenAI 兼容客户端
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_id = model_id
        
        # 实例化 Stateful Agents
        self.agents = {
            "Alpha": StatefulAgent("Alpha", "Neutral"),
            "Beta": StatefulAgent("Beta", "Skeptical")
        }
        
        # 会话记忆 (OpenAI 格式: list of dicts)
        self.history = { "Alpha": [], "Beta": [] }
        
        # 图状态：标记某个 Agent 是否还在局内（False 代表被 Dropout）
        self.active_nodes = { "Alpha": True, "Beta": True }
        
        # 统计数据
        self.total_tokens_used = 0
        self.curator_interventions = 0

    async def call_agent(self, role: str, prompt: str) -> str:
        """
        根据 Agent 当前的 emotional state 生成回复。
        """
        agent = self.agents[role]
        
        # 构建消息
        messages = [{"role": "system", "content": agent.build_current_prompt()}]
        
        # 添加历史记录
        self.history[role].append({"role": "user", "content": prompt})
        
        # 历史记录剪枝：仅保留最近 4 条对话 (2 对)，避免长文本迷失
        if len(self.history[role]) > 4:
            self.history[role] = self.history[role][-4:]
            
        messages.extend(self.history[role])
        
        response = await self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            temperature=0.2,   # 降低随机性，强化逻辑
            max_tokens=800    # 物理截断，严禁 yapping
        )
        
        self.total_tokens_used += response.usage.total_tokens
            
        reply_text = response.choices[0].message.content
        self.history[role].append({"role": "assistant", "content": reply_text})
        
        return reply_text

    async def run_collaboration(self, task: str, max_turns: int = 4) -> dict:
        """
        多智能体心跳循环，带有基于生理信号的截断与状态跃迁。
        """
        result = {
            "task": task,
            "status": "MAX_TURNS_REACHED",
            "turns": 0,
            "final_answer": "",
            "tokens_used": 0,
            "curator_interventions": 0
        }
        
        # Turn 1: Alpha 初始提案
        print("\n[MAS Controller] Alpha 生成初始方案...")
        last_alpha_msg = await self.call_agent("Alpha", f"Task: {task}")
        result["final_answer"] = last_alpha_msg
        
        for turn in range(1, max_turns + 1):
            result["turns"] = turn
            
            # Beta Node Check
            if not self.active_nodes["Beta"]:
                break
                
            print(f"\n[Turn {turn}] Beta 执行反驳...")
            beta_prompt = f"Target Proposal to verify:\n{last_alpha_msg}"
            last_beta_msg = await self.call_agent("Beta", beta_prompt)
            result["final_answer"] = last_beta_msg
            
            # Physio-Curator: 多模态信号校验（传入历史相似度记录）
            print(f"[Turn {turn}] 🧠 Physio-Curator (融合 EEG & 语义) 判断中...")
            
            if not hasattr(self, 'd_sem_history'):
                self.d_sem_history = []
                
            is_lazy, reason, d_sem, p_eeg = await check_physio_lazy_agreement(
                self.client,
                last_alpha_msg,
                last_beta_msg,
                turn_index=turn,
                d_sem_history=self.d_sem_history
            )
            
            # 更新历史相似度记录（在计算出当前 d_sem 之后）
            self.d_sem_history.append(d_sem)
            
            print(f"   => D_sem (语义相似度): {d_sem:.3f} | P_eeg (专注衰减): {p_eeg:.2f}")
            
            if is_lazy:
                # 收到强制干预，Beta 状态重塑
                self.curator_interventions += 1
                result["curator_interventions"] += 1
                print(f"🚨 Physio-Curator 干预触发 ({reason}). 迫使 Beta 进入 Aggressive/Skeptical 回炉！")
                
                # 回滚历史
                if len(self.history["Beta"]) >= 2:
                    self.history["Beta"].pop() 
                    self.history["Beta"].pop()
                
                # 强制转移并重写
                self.agents["Beta"].transition_state("", curator_force="Aggressive")
                force_prompt = beta_prompt + "\n\n[PHYSIO-CURATOR SIGNAL]: Wake up! Your previous response was highly similar to the original text and caused a drop in human monitoring focus. Re-attack this argument aggressively."
                last_beta_msg = await self.call_agent("Beta", force_prompt)
                result["final_answer"] = last_beta_msg
                
            # Beta 自身正常状态跃迁更新
            self.agents["Beta"].transition_state(last_alpha_msg, is_lazy=is_lazy)

            # Node Dropout 判定：基于自适应相似度阈值
            # 早期轮次需要更高的相似度才能触发 dropout（避免过早收敛）
            dropout_threshold = 0.88 if turn < 2 else 0.82  # 早期更严格
            if d_sem > dropout_threshold and not is_lazy:
                print(f"✅ 达成真实高质量共识！触发 Node Dropout (Beta 节点离线)")
                self.active_nodes["Beta"] = False
                result["status"] = "CONVERGED_AND_DROPOUT"
                break
            
            # Alpha Node Check & Reply
            if self.active_nodes["Alpha"] and turn < max_turns:
                 self.agents["Alpha"].transition_state(last_beta_msg)
                 
                 print(f"\n[Turn {turn}] Alpha 基于 Beta 的反馈准备应对...")
                 alpha_prompt = f"Challenge received from Challenger:\n{last_beta_msg}\n\nPlease adapt or defend."
                 last_alpha_msg = await self.call_agent("Alpha", alpha_prompt)
                 result["final_answer"] = last_alpha_msg

        result["tokens_used"] = self.total_tokens_used
        return result
