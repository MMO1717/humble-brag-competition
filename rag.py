import json
import faiss
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from schema import SocialContext
import pickle
import os

class MetaStringRAG:
    """
    基于 Meta-String 的 RAG 系统
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化 RAG 系统
        :param model_name: 用于嵌入的模型名称
        """
        self.model_name = model_name
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.index = None
        self.meta_strings = []
        self.social_contexts = []

    def build_index(self, social_contexts: List[SocialContext]):
        """
        构建 FAISS 索引
        :param social_contexts: 社交上下文列表
        """
        self.social_contexts = social_contexts
        self.meta_strings = [ctx.to_metastring() for ctx in social_contexts]

        # 生成嵌入向量
        embeddings = self.embeddings.embed_documents(self.meta_strings)
        embeddings_np = np.array(embeddings).astype('float32')

        # 创建 FAISS 索引
        dimension = embeddings_np.shape[1]
        self.index = faiss.IndexFlatL2(dimension)

        # 添加嵌入到索引
        self.index.add(embeddings_np)

        print(f"成功构建包含 {len(self.meta_strings)} 个条目的索引")

    def search(self, query_metastring: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相似的 Meta-String
        :param query_metastring: 查询的 Meta-String
        :param k: 返回结果数量
        :return: 相似结果列表
        """
        if self.index is None:
            raise ValueError("索引尚未构建，请先调用 build_index 方法")

        # 对查询进行嵌入
        query_embedding = self.embeddings.embed_query(query_metastring)
        query_embedding = np.array([query_embedding]).astype('float32')

        # 执行搜索
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx < len(self.meta_strings):  # 确保索引有效
                results.append({
                    'distance': float(distances[0][i]),
                    'meta_string': self.meta_strings[idx],
                    'social_context': self.social_contexts[idx],
                    'similarity_score': 1 / (1 + float(distances[0][i]))  # 转换为相似度分数
                })

        return results

    def save_index(self, filepath: str):
        """
        保存索引到文件
        :param filepath: 保存路径
        """
        if self.index is None:
            raise ValueError("索引尚未构建")

        # 保存 FAISS 索引
        faiss.write_index(self.index, f"{filepath}.index")

        # 保存元数据
        metadata = {
            'meta_strings': self.meta_strings,
            'social_contexts': [ctx.dict() for ctx in self.social_contexts]
        }

        with open(f"{filepath}.metadata", 'wb') as f:
            pickle.dump(metadata, f)

        print(f"索引已保存到 {filepath}")

    def load_index(self, filepath: str):
        """
        从文件加载索引
        :param filepath: 加载路径
        """
        # 加载 FAISS 索引
        self.index = faiss.read_index(f"{filepath}.index")

        # 加载元数据
        with open(f"{filepath}.metadata", 'rb') as f:
            metadata = pickle.load(f)

        self.meta_strings = metadata['meta_strings']
        self.social_contexts = [SocialContext(**ctx) for ctx in metadata['social_contexts']]

        print(f"索引已从 {filepath} 加载")

    def add_context(self, social_context: SocialContext):
        """
        向现有索引添加新的社交上下文
        :param social_context: 新的社交上下文
        """
        if self.index is None:
            # 如果索引不存在，初始化
            self.build_index([social_context])
        else:
            # 将新上下文添加到现有列表
            self.social_contexts.append(social_context)
            meta_string = social_context.to_metastring()
            self.meta_strings.append(meta_string)

            # 生成新嵌入并添加到索引
            new_embedding = self.embeddings.embed_query(meta_string)
            new_embedding = np.array([new_embedding]).astype('float32')

            self.index.add(new_embedding)

            print(f"已添加新的社交上下文到索引")


def create_sample_data():
    """
    创建示例数据用于测试
    """
    from schema import PlatformEnum, RelationshipEnum, AgentRoleEnum, InteractionGoalEnum, PostTypeEnum

    sample_contexts = [
        SocialContext(
            platform=PlatformEnum.WECHAT_MOMENTS,
            relationship=RelationshipEnum.FRIEND,
            agent_role=AgentRoleEnum.FRIEND,
            interaction_goal=InteractionGoalEnum.FAVORABLE_RESPONSE,
            post_content="今天跑了三个客户，好累呀",
            post_type=PostTypeEnum.STATUS_UPDATE,
            sender_name="小王"
        ),
        SocialContext(
            platform=PlatformEnum.XIAOHONGSHU,
            relationship=RelationshipEnum.COLLEAGUE,
            agent_role=AgentRoleEnum.COLLEAGUE,
            interaction_goal=InteractionGoalEnum.INFORMATION_SHARING,
            post_content="分享一下最近学到的新技能",
            post_type=PostTypeEnum.INFORMATION_SHARING,
            sender_name="李同事"
        ),
        SocialContext(
            platform=PlatformEnum.WEIBO,
            relationship=RelationshipEnum.FAMILY,
            agent_role=AgentRoleEnum.FAMILY_MEMBER,
            interaction_goal=InteractionGoalEnum.EMPATHETIC_SUPPORT,
            post_content="今天心情不太好，需要一些鼓励",
            post_type=PostTypeEnum.EMOTIONAL_OUTBURST,
            sender_name="妈妈"
        ),
        SocialContext(
            platform=PlatformEnum.TIKTOK,
            relationship=RelationshipEnum.STRANGER,
            agent_role=AgentRoleEnum.ACQUAINTANCE,
            interaction_goal=InteractionGoalEnum.MAINTAIN_DISTANCE,
            post_content="这是一个有趣的视频，值得一看",
            post_type=PostTypeEnum.LIFE_MOMENT,
            sender_name="路人甲"
        ),
        SocialContext(
            platform=PlatformEnum.LINKEDIN,
            relationship=RelationshipEnum.CLIENT,
            agent_role=AgentRoleEnum.SERVICE_PROVIDER,
            interaction_goal=InteractionGoalEnum.PROMOTION,
            post_content="我们公司最近推出了新产品",
            post_type=PostTypeEnum.PRODUCT_PROMOTION,
            sender_name="张总"
        )
    ]

    return sample_contexts


if __name__ == "__main__":
    # 创建示例数据
    sample_data = create_sample_data()

    # 初始化 RAG 系统
    rag_system = MetaStringRAG()

    # 构建索引
    rag_system.build_index(sample_data)

    # 创建一个查询示例
    query_context = SocialContext(
        platform=PlatformEnum.WECHAT_MOMENTS,
        relationship=RelationshipEnum.FRIEND,
        agent_role=AgentRoleEnum.FRIEND,
        interaction_goal=InteractionGoalEnum.EMPATHETIC_SUPPORT,
        post_content="今天工作特别累，感觉压力好大"
    )

    query_metastring = query_context.to_metastring()
    print(f"查询: {query_metastring}\n")

    # 执行搜索
    results = rag_system.search(query_metastring, k=3)

    print("最相似的结果:")
    for i, result in enumerate(results, 1):
        print(f"{i}. 相似度: {result['similarity_score']:.3f}")
        print(f"   Meta-String: {result['meta_string']}")
        print(f"   距离: {result['distance']:.3f}\n")

    # 保存索引以供后续使用
    rag_system.save_index("./faiss_index")