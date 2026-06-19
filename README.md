# Excel Python 练习与每日新闻邮件

本仓库保留原有 Excel/Pandas 练习脚本，并新增每日中文新闻邮件自动化。

## 每日 9 点新闻邮件

`.github/workflows/daily-news-email.yml` 会在每天北京时间 09:00 自动运行
`daily_news_email.py`，并向 `1057742284@qq.com` 分别发送三封中文图文邮件：

- AI 新闻
- 美股新闻
- 世界杯新闻

邮件内容来自公开中文新闻 RSS 搜索源，HTML 模板包含横幅图、新闻图片卡片、摘要、来源和阅读全文按钮。

## 邮件发送配置

需要在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中配置以下 Secrets：

| Secret | 必填 | 说明 |
| --- | --- | --- |
| `SMTP_HOST` | 是 | SMTP 服务器地址，例如 `smtp.gmail.com` |
| `SMTP_PORT` | 否 | SMTP 端口，默认 `587` |
| `SMTP_USERNAME` | 视服务器而定 | SMTP 登录账号 |
| `SMTP_PASSWORD` | 视服务器而定 | SMTP 登录密码或应用专用密码 |
| `SMTP_FROM` | 否 | 发件人邮箱，默认使用 `SMTP_USERNAME` |
| `SMTP_FROM_NAME` | 否 | 发件人名称，默认 `每日新闻助手` |
| `SMTP_USE_TLS` | 否 | 是否启用 STARTTLS，默认 `true` |
| `SMTP_USE_SSL` | 否 | 是否直接使用 SSL，默认 `false` |

如果使用 Gmail 发信，通常需要配置：

- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `SMTP_USERNAME=<发件 Gmail 地址>`
- `SMTP_PASSWORD=<Google 应用专用密码>`
- `SMTP_FROM=<发件 Gmail 地址>`

## 本地预览

不发送邮件，只生成 HTML 和纯文本预览：

```bash
python daily_news_email.py --dry-run --output-dir news_previews
```

只预览其中一个分类：

```bash
python daily_news_email.py --dry-run --category ai
```
