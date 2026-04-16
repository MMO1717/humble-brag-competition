"""
mas_controller.py
异步多智能体调度器，协调 Alpha、Beta 的异步生成和 Curator 的评估与剪枝。
"""

import asyncio
from google import genai
from google.genai import types
from agents import get_agent_config
from curator import check_lazy_agreement, dynamic_edge_pruning

class MAS_Controller:
    def __init__(self, api_key: str, model_id: str):
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        self.model_id = model_id
        
        # 保存各 Agent 的对话上下文历史（内容为 types.Content）
        self.history = {
            "Alpha": [],
            "Beta": []
        }
        
        # 记录 Token 消耗
        self.total_tokens_used = 0
        self.curator_interventions = 0 # Curator 强制干预(FORCE_SKEPTICAL)次数

    async def call_agent(self, role: str, prompt: str, reset_history: bool = False) -> str:
        """
        调用指定的 Agent (Alpha或Beta)。
        """
        config = get_agent_config(role)
        
        if reset_history:
            self.history[role] = []
            
        # 准备用户输入
        user_content = types.Content(role="user", parts=[types.Part(text=prompt)])
        self.history[role].append(user_content)
        
        # 生成请求配置
        gen_config = types.GenerateContentConfig(
            system_instruction=config["system_prompt"],
            temperature=0.7
        )
        
        # 调用大模型 (使用 aio 异步接口)
        response = await self.client.aio.models.generate_content(
            model=self.model_id,
            contents=self.history[role],
            config=gen_config
        )
        
        # 累加 Token (包含 input, outputTokens 会被汇总在 usage_metadata.total_token_count 里)
        if response.usage_metadata:
            self.total_tokens_used += response.usage_metadata.total_token_count
            
        reply_text = response.text
        
        # 记录助手回复
        model_content = types.Content(role="model", parts=[types.Part(text=reply_text)])
        self.history[role].append(model_content)
        
        return reply_text

    async def run_collaboration(self, task: str, max_turns: int = 3, use_curator: bool = True) -> dict:
        """
        执行多智能体协作流（支持开启或关闭 Curator 以进行对照实验）。
        """
        result = {
            "task": task,
            "status": "MAX_TURNS_REACHED",
            "turns": 0,
            "final_alpha": "",
            "final_beta": "",
            "tokens_used": 0,
            "curator_interventions": 0
        }
        
        # 1. 第 1 轮：Alpha 给出初稿
        resp_alpha = await self.call_agent("Alpha", f"Task: {task}")
        result["final_alpha"] = resp_alpha
        
        # 开始对话循环
        for turn in range(1, max_turns + 1):
            result["turns"] = turn
            print(f"\n[Turn {turn}] Alpha 结论已生成，交由 Beta 审查...")
            
            # 2. Beta 进行审查
            beta_prompt = f"针对此任务: '{task}'\nAgent Alpha 的当前答案是:\n{resp_alpha}\n\n请进行严格的逻辑校验和反驳（Step-wise Verification）。"
            resp_beta = await self.call_agent("Beta", beta_prompt)
            result["final_beta"] = resp_beta
            print(f"[Turn {turn}] Beta 审查完毕。")
            
            # 如果不使用 Curator，直接进入下一轮 Alpha 回应
            if not use_curator:
                if turn < max_turns:
                    resp_alpha = await self.call_agent("Alpha", f"Agent Beta 反驳了你:\n{resp_beta}\n\n请回应反驳并修正你的答案，或者坚持原有正确立场。")
                    result["final_alpha"] = resp_alpha
                continue
                
            # 3. Curator 介入 (使用 Level 1 规则防御 + Gamma 动态评估)
            print(f"[Turn {turn}] 🔍 Curator (Gamma) 介入评估中...")
            
            # 步骤 3.1: 快速懒惰检测
            if check_lazy_agreement(resp_alpha, resp_beta):
                self.curator_interventions += 1
                result["curator_interventions"] += 1
                print(f"🚨 [Curator 干预] 检测到 Beta 弱势/虚假附和！强制 Beta 进入深度 Skeptical 状态并重写。")
                
                # 扔掉 Beta 最近一条没出息的历史，强制它重写
                self.history["Beta"].pop() 
                self.history["Beta"].pop()
                force_prompt = beta_prompt + "\n\n[CURATOR WARNING]: Your previous analysis lacked depth or showed Lazy Agreement. Restart your evaluation with MAXIMUM SKEPTICISM and detailed Rationale."
                resp_beta = await self.call_agent("Beta", force_prompt)
                result["final_beta"] = resp_beta
            
            # 步骤 3.2: 深度动态评估（判断是否收敛）
            gamma_signal, gamma_usage = await dynamic_edge_pruning(
                self.client, self.model_id, task, resp_alpha, resp_beta
            )
            
            # 将 Gamma 的 token 加进去
            if gamma_usage:
                self.total_tokens_used += gamma_usage.total_token_count
                
            signal_status = gamma_signal.get("status", "CONTINUE")
            print(f"📊 [Curator 信号]: {signal_status} | 评分: {gamma_signal.get('consensus_score', 'N/A')} | 理由: {gamma_signal.get('reason', '')}")
            
            if signal_status == "CONVERGED":
                print("✅ 剪枝！达成高质量共识，提前终止通信以节省 Token。")
                result["status"] = "CONVERGED"
                break
            elif signal_status == "FORCE_SKEPTICAL":
                # 由大模型 Gamma 判断出的深度逻辑软弱，同样重写
                self.curator_interventions += 1
                result["curator_interventions"] += 1
                print(f"🚨 [Curator 干预-深度] 逻辑软弱，强制 Beta 重新深挖漏洞！")
                self.history["Beta"].pop() 
                self.history["Beta"].pop()
                force_prompt = beta_prompt + f"\n\n[CURATOR WARNING]: {gamma_signal.get('reason')} Reboot and rethink."
                resp_beta = await self.call_agent("Beta", force_prompt)
                result["final_beta"] = resp_beta
            
            # 如果没结束，Alpha 接收 Beta 的观点并准备下一轮
            if turn < max_turns:
                 resp_alpha = await self.call_agent("Alpha", f"Agent Beta 指出了你的问题:\n{resp_beta}\n\n请回应反驳并修正答案，若你没发觉自己有错请理性坚持。")
                 result["final_alpha"] = resp_alpha

        # 结算
        result["tokens_used"] = self.total_tokens_used
        return result
