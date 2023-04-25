FROM redis/redis-stack:latest
LABEL maintainer freebrOuyang
# Overwrite conf file
COPY docker-files/redis/redis-stack.conf /redis-stack.conf