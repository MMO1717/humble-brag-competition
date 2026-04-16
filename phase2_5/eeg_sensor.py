"""
eeg_sensor.py
构建与物理世界（TGAM-Glas 硬件）桥接的数据总线模块。
附带 Mock 开关，方便在无实际硬件时离线测试 Physi-Signal (关注度)。
"""

import time
import random
import threading
from collections import deque

class EEGSensorQueue:
    def __init__(self, use_mock: bool = True, max_len: int = 60):
        """
        初始化传感器队列。
        Args:
            use_mock: 是否使用模拟生成的假数据
            max_len: 保存最近 T 秒的采样数据（1Hz 采样即保存最近60条）
        """
        self.use_mock = use_mock
        self.attention_queue = deque(maxlen=max_len)
        self.meditation_queue = deque(maxlen=max_len)
        self.lock = threading.Lock()
        self._running = False
        
        # 模拟当前人类状态，控制 Mock 递减趋势
        self._mock_human_state = "attentive" 
        self._current_attention = 80.0
        
    def start_sampling(self):
        # [PROMPT-ONLY MODE] 暂时屏蔽硬件/Mock 轮询线程，不产生后台开销
        self._running = False
        # self.thread = threading.Thread(target=self._sample_loop, daemon=True)
        # self.thread.start()
        print("🔌 [EEG Sensor] Prompt 专注模式：传感器后台线程已静默 (No-Op).")
        
    def stop_sampling(self):
        self._running = False
        if hasattr(self, 'thread'):
            self.thread.join()
            
    def set_mock_human_fatigue(self, is_fatigued: bool):
        """人为干预模拟器，使其模拟出人类实验者失去焦点的情况"""
        self._mock_human_state = "fatigued" if is_fatigued else "attentive"
            
    def _sample_loop(self):
        while self._running:
            if self.use_mock:
                # Mock 逻辑：正常人在听有意义辩论时专注度80左右，疲劳/听到废话时掉到40以下
                if self._mock_human_state == "attentive":
                    # 缓慢回升并加入白噪声
                    self._current_attention = min(100.0, self._current_attention + random.uniform(0, 5))
                else: # fatigued
                    # 快速衰减并加入白噪声
                    self._current_attention = max(0.0, self._current_attention - random.uniform(5, 15))
                    
                attention = self._current_attention + random.uniform(-2, 2)
                meditation = 50.0 + random.uniform(-10, 10)
            else:
                # TODO: 接入真实的 TGAM 串口流代码 (如 mindwave-python)
                attention = 0.0
                meditation = 0.0
                raise NotImplementedError("Real TGAM hardware interface not yet implemented!")
                
            with self.lock:
                self.attention_queue.append(attention)
                self.meditation_queue.append(meditation)
                
            time.sleep(1) # 1Hz
            
    def get_attention_gradient(self, window: int = 5) -> float:
        """
        [PROMPT-ONLY MODE] 恒定返回 0.0 梯度。
        """
        return 0.0
            
# 全局单例
eeg_sensor_instance = EEGSensorQueue()
