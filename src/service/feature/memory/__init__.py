try:
    from .redismem import RedisMemory
except ImportError:
    print("Redis not installed. Skipping import.")
    RedisMemory = None

def get_memory(cfg, init=False):
    memory = None
    # if not PineconeMemory:
    #     print("Error: Pinecone is not installed. Please install pinecone"
    #           " to use Pinecone as a memory backend.")
    # else:
    #     memory = PineconeMemory(cfg)
    #     if init:
    #         memory.clear()
    if not RedisMemory:
        print("Error: Redis is not installed. Please install redis-py to use Redis as a memory backend.")
    else:
        memory = RedisMemory(cfg)
    return memory