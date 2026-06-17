# 每日中文新闻邮件

本仓库包含一个 GitHub Actions 自动化任务：每天北京时间 09:00 向
`w1057742284@gmail.com` 分别发送三封中文图文新闻邮件：

1. AI 新闻
2. 美股新闻
3. 世界杯新闻

邮件内容由 `daily_news_email.py` 从公开中文新闻 RSS 聚合获取，并渲染为带头图、摘要卡片和阅读全文按钮的 HTML 邮件，同时包含纯文本备用版本。

## GitHub Secrets 配置

在仓库的 `Settings -> Secrets and variables -> Actions` 中配置：

| Secret | 必填 | 说明 |
| --- | --- | --- |
| `SMTP_HOST` | 是 | SMTP 服务器地址，例如 `smtp.gmail.com` |
| `SMTP_USERNAME` | 是 | SMTP 用户名，通常是发件邮箱 |
| `SMTP_PASSWORD` | 是 | SMTP 密码或邮箱服务商授权码 |
| `SMTP_PORT` | 否 | SMTP 端口，默认 `587` |
| `SMTP_FROM` | 否 | 发件邮箱，默认使用 `SMTP_USERNAME` |
| `SMTP_FROM_NAME` | 否 | 发件人名称，默认 `每日中文新闻` |

工作流文件位于 `.github/workflows/daily-news-email.yml`，定时配置为
`0 1 * * *`，即 UTC 01:00 / 北京时间 09:00。

## 本地验证

只抓取新闻并预览文本，不发送邮件：

```bash
python daily_news_email.py --dry-run
```

只验证某一类新闻：

```bash
python daily_news_email.py --dry-run --category ai
python daily_news_email.py --dry-run --category us_stocks
python daily_news_email.py --dry-run --category world_cup
```

正式发送时需先在环境变量中提供 SMTP 配置。
