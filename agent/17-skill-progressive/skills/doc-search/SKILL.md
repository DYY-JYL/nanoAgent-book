---
name: doc-search
description: 本地文档知识库检索，支持分层导航和渐进式检索。Use when user asks to 查文档, 搜索知识库, 找资料, 查制度。
---

# 文档知识库检索 Skill

## 快速开始
1. 先调用 read_file("skills/doc-search/data_structure.md") 查看目录索引
2. 根据目录描述定位到目标子目录或文件
3. 调用 read_file 读取目标文件内容
4. 信息不足时调整关键词重试，最多 5 轮

## 检索策略
- 从 data_structure.md 开始，逐层导航到目标文件
- 优先局部读取，不要一次性读取大文件
- 信息缺失时如实说明，不要猜测

## 禁止行为
- 不要跳过 data_structure.md 直接猜测文件路径
- 不要一次性读取超过 200 行的内容
