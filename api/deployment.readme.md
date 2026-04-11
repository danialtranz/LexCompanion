docker run -d \
 --name postgres-lex \
 -e POSTGRES_USER=hungtch \
 -e POSTGRES_PASSWORD='@admin21a1!!2' \
 -e POSTGRES_DB=lex_companion \
 -e TZ=Asia/Ho_Chi_Minh \
 -p 5444:5432 \
 -v postgres_lex_data:/var/lib/postgresql/data \
 --restart always \
 postgres:latest

docker run -d \
 --name minio-lex \
 -p 6502:9000 \
 -p 6503:9001 \
 -e MINIO_ROOT_USER=hung21az \
 -e MINIO_ROOT_PASSWORD='@admin21a1!!2' \
 -e MINIO_REGION=us-east-1 \
 -e TZ=Asia/Ho_Chi_Minh \
 -v minio_lex_data:/data \
 --restart always \
 minio/minio server /data --console-address ":9001"

docker run -d \
 --name redis_server \
 --restart=always \
 -p 6375:6379 \
 -v redis_data:/data \
 redis:7.2 \
 redis-server --requirepass "redispassword!" --appendonly yes
