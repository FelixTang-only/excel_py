# Excel Python 练习与每日新闻邮件

本仓库新增了每日中文新闻邮件自动化：GitHub Actions 会在北京时间每天 09:00
运行 `daily_news_email.py`，并分别发送三封图文 HTML 邮件到
`w1057742284@gmail.com`：

- AI 新闻早报
- 美股新闻早报
- 世界杯新闻早报

## 邮件发送配置

在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中添加以下
Secrets：

| Secret | 说明 |
| --- | --- |
| `SMTP_HOST` | SMTP 服务器地址，例如 `smtp.gmail.com` |
| `SMTP_PORT` | SMTP 端口，常见为 `587` 或 `465` |
| `SMTP_USERNAME` | SMTP 登录账号 |
| `SMTP_PASSWORD` | SMTP 登录密码或邮箱应用专用密码 |
| `SMTP_FROM` | 可选，发件人地址；未配置时使用 `SMTP_USERNAME` |
| `SMTP_USE_TLS` | 可选，默认 `true`；端口 `465` 会自动使用 SSL |

配置完成后，工作流会按 `.github/workflows/daily-news-email.yml` 中的 cron
自动运行，也可以在 GitHub Actions 页面手动执行 `Daily Chinese News Email`。

本地预览可运行：

```bash
python daily_news_email.py --dry-run
```
