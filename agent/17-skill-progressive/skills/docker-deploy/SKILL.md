---
name: docker-deploy
description: Docker 容器化部署，支持 build / up / down / 健康检查。Use when user asks to deploy, docker, 容器部署, 上线。
---

# Docker Deploy Skill

## 前置检查
1. 确认项目根目录存在 Dockerfile
2. 确认存在 docker-compose.yml（可选）

## 部署步骤

### 单容器部署
```bash
docker build -t <image_name> .
docker run -d --name <container_name> -p <host_port>:<container_port> <image_name>
```

### Compose 部署
```bash
docker-compose build
docker-compose up -d
docker-compose ps  # 验证状态
```

## 健康检查
```bash
docker ps --filter "name=<container_name>"
curl -f http://localhost:<port>/health || echo "Health check failed"
```

## 回滚
```bash
docker-compose down
docker-compose up -d --build
```

## 注意事项
- 生产环境部署前务必确认 .env 文件不包含敏感信息
- 确保端口未被占用
- 建议先在本地用 docker-compose up 测试
