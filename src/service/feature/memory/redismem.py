"""Redis memory provider."""
from base64 import b64decode
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from logging import getLogger, Logger
from typing import Any, List, Optional
import numpy as np
import redis

from .base import MemoryProviderSingleton, get_ada_embedding
from configure import Config
from definition.const import EXPIRE_TIME_MEMORY
from definition.var import is_docker

DIMENSION_VECTORS = 1536
SCHEMA = [
    TextField("data"),
    VectorField(
        "embedding",
        "HNSW",
        {
            "TYPE": "FLOAT32",
            "DIM": DIMENSION_VECTORS,
            "DISTANCE_METRIC": "COSINE"
        }
    ),
]

class RedisMemory(MemoryProviderSingleton):
    db: redis.Redis
    redis_config: dict
    index_name: str
    logger: Logger = None
    def __init__(self, cfg: Config):
        """
        初始化 Redis 记忆服务
        """
        self.logger = getLogger('REDISMEM')
        redis_config = cfg.data.databases['Redis']
        self.index_name = redis_config.get('IndexName')

        redis_host = redis_config.get('Production' if is_docker() else 'Development').get('Host')
        redis_port = redis_config.get('Production' if is_docker() else 'Development').get('Port')
        redis_password = b64decode(redis_config.get('Password')).decode()
        
        self.dimension = DIMENSION_VECTORS
        self.db = redis.Redis(
            host=redis_host,
            port=redis_port,
            username='default',
            password=redis_password,
            db=0,
        )
        try:
            self.db.ft(self.index_name).create_index(
                fields=SCHEMA,
                definition=IndexDefinition(
                    prefix=[f"{self.index_name}:"],
                    index_type=IndexType.HASH
                    )
                )
        except Exception as e:
            if str(e) != 'Index already exists':
                self.logger.error('创建 Redis 搜索索引失败：%s', str(e))
        existing_vec_num = self.db.get(f'{self.index_name}-vec_num')
        self.vec_num = int(existing_vec_num.decode('utf-8')) if\
            existing_vec_num else 0

    def add(self, data: str) -> str:
        """
        添加数据到 Redis 记忆中
        返回添加后的记忆数量
        """
        if 'Command Error:' in data:
            return ''
        vector = get_ada_embedding(data)
        vector = np.array(vector).astype(np.float32).tobytes()
        data_dict = {
            b'data': data,
            'embedding': vector
        }
        hash_name = f'{self.index_name}:{self.vec_num}'
        pipe = self.db.pipeline()
        pipe.hset(hash_name, mapping=data_dict)
        pipe.expire(hash_name, EXPIRE_TIME_MEMORY)
        self.vec_num += 1
        pipe.set(f'{self.index_name}-vec_num', self.vec_num)
        pipe.execute()
        return self.vec_num

    def get(self, data: str) -> Optional[List[Any]]:
        """
        返回 Redis 记忆中与 data 最相关的信息
        """
        return self.get_relevant(data, 1)

    def clear(self) -> str:
        """
        清空 Redis 记忆信息
        """
        self.db.flushall()
        return True

    def get_relevant(
        self,
        data: str,
        num_relevant: int = 5
    ) -> Optional[List[Any]]:
        """
        返回 Redis 记忆中与 data 最相关的 num_relevant 条信息列表
        """
        query_embedding = get_ada_embedding(data)
        base_query = f'*=>[KNN {num_relevant} @embedding $vector AS vector_score]'
        query = Query(base_query).return_fields(
            'data',
            'vector_score'
        ).sort_by('vector_score').dialect(2)
        query_vector = np.array(query_embedding).astype(np.float32).tobytes()

        try:
            results = self.db.ft(self.index_name).search(
                query, query_params={'vector': query_vector}
            )
        except Exception as e:
            self.logger.error('执行 Redis 搜索失败：%s', str(e))
            return None
        return [result.data for result in results.docs]

    def get_stats(self):
        """
        返回 Redis 记忆的使用情况
        """
        return self.db.ft(self.index_name).info()
