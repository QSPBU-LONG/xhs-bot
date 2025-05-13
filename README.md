# XHS Bot 自动化评论工具

一个基于 Selenium 和 undetected-chromedriver 的自动化脚本，用于在小红书自动搜索关键词并发表评论。

## 功能简介

- 登录小红书网页端（支持扫码或短信登录）
- 自动搜索指定关键词
- 自动提取帖子链接
- 自动发布预设评论
- 可保存并加载登录 Cookie（由于小红书无法保存暂时移除该功能）

## 使用方法

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 运行脚本：

```bash
python web_agent.py
```

首次运行请等待页面刷新稳定之后手动扫码登录。

## 配置项说明

请在 `config.py` 文件中自定义以下内容：

- `keywords`: 要搜索的关键词列表
- `comments`: 随机评论内容列表
- `private_message`: 预设私信内容
- `*_interval`: 各类延时区间（防止被风控）

## 注意事项

- 使用脚本有被平台风控的风险，请勿频繁运行。
