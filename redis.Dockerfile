FROM redis:latest
LABEL maintainer freebrOuyang
# Overwrite conf file
COPY docker-files/redis/redis.conf /data/redis.conf
ENTRYPOINT ["redis-server", "/data/redis.conf", "--appendonly yes"]
