#!/usr/bin/env python3
"""Send three daily Chinese news emails with rich HTML layouts.

The script intentionally uses only Python's standard library so it can run
directly in GitHub Actions without dependency installation.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import smtplib
import ssl
import sys
import textwrap
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import Iterable

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.8 fallback.
    ZoneInfo = None  # type: ignore[assignment]


RECIPIENT = "w1057742284@gmail.com"
DEFAULT_ITEM_LIMIT = 6
FETCH_TIMEOUT_SECONDS = 20
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


@dataclass(frozen=True)
class NewsCategory:
    key: str
    title: str
    subject_prefix: str
    query: str
    accent_color: str
    soft_color: str
    hero_image: str
    intro: str


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    source: str
    summary: str
    published_at: datetime | None


CATEGORIES: tuple[NewsCategory, ...] = (
    NewsCategory(
        key="ai",
        title="AI 新闻",
        subject_prefix="每日 AI 新闻",
        query="人工智能 AI 大模型 科技 最新 when:1d",
        accent_color="#6d5dfc",
        soft_color="#f1efff",
        hero_image=(
            "https://images.unsplash.com/photo-1677442136019-21780ecad995"
            "?auto=format&fit=crop&w=1200&q=80"
        ),
        intro="精选过去一天人工智能、生成式 AI、大模型和产业应用的重要动态。",
    ),
    NewsCategory(
        key="us_stocks",
        title="美股新闻",
        subject_prefix="每日美股新闻",
        query="美股 纳斯达克 标普 道琼斯 财报 最新 when:1d",
        accent_color="#0f9f6e",
        soft_color="#eaf8f2",
        hero_image=(
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3"
            "?auto=format&fit=crop&w=1200&q=80"
        ),
        intro="聚合隔夜美股、科技股、指数、财报和宏观市场的核心消息。",
    ),
    NewsCategory(
        key="world_cup",
        title="世界杯新闻",
        subject_prefix="每日世界杯新闻",
        query="世界杯 足球 国际足联 预选赛 最新 when:1d",
        accent_color="#d97706",
        soft_color="#fff7ed",
        hero_image=(
            "https://images.unsplash.com/photo-1518091043644-c1d4457512c6"
            "?auto=format&fit=crop&w=1200&q=80"
        ),
        intro="追踪世界杯、预选赛、球队阵容、赛程和国际足联相关最新报道。",
    ),
)


def get_china_now() -> datetime:
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo("Asia/Shanghai"))
    return datetime.now(timezone(timedelta(hours=8)))


def build_google_news_rss_url(query: str) -> str:
    params = {
        "q": query,
        "hl": "zh-CN",
        "gl": "CN",
        "ceid": "CN:zh-Hans",
    }
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        return response.read()


def strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def compact_text(value: str, max_length: int) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def normalized_title(title: str) -> str:
    title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
    return re.sub(r"\s+", " ", title).lower()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def parse_google_news_feed(xml_bytes: bytes, limit: int) -> list[NewsItem]:
    root = ET.fromstring(xml_bytes)
    items: list[NewsItem] = []
    seen_titles: set[str] = set()

    for item in root.findall("./channel/item"):
        raw_title = strip_tags(item.findtext("title", default=""))
        link = item.findtext("link", default="").strip()
        source = item.findtext("source", default="").strip() or "Google 新闻"
        description = strip_tags(item.findtext("description", default=""))
        title = re.sub(r"\s+-\s+[^-]+$", "", raw_title).strip() or raw_title
        key = normalized_title(title)

        if not title or not link or key in seen_titles:
            continue

        seen_titles.add(key)
        items.append(
            NewsItem(
                title=compact_text(title, 120),
                link=link,
                source=compact_text(source, 32),
                summary=compact_text(description, 180),
                published_at=parse_datetime(item.findtext("pubDate")),
            )
        )

        if len(items) >= limit:
            break

    return items


def fetch_category_news(category: NewsCategory, limit: int) -> list[NewsItem]:
    url = build_google_news_rss_url(category.query)
    return parse_google_news_feed(fetch_url(url), limit)


def format_chinese_datetime(value: datetime | None) -> str:
    if value is None:
        return "发布时间待确认"

    china_tz = ZoneInfo("Asia/Shanghai") if ZoneInfo is not None else timezone(timedelta(hours=8))
    local_value = value.astimezone(china_tz)
    return local_value.strftime("%m月%d日 %H:%M")


def article_cards(items: Iterable[NewsItem], category: NewsCategory) -> str:
    cards: list[str] = []

    for index, item in enumerate(items, start=1):
        summary = item.summary or "点击查看完整报道和更多背景信息。"
        cards.append(
            f"""
            <tr>
              <td style="padding:0 24px 18px 24px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                  style="border:1px solid #e5e7eb;border-radius:18px;background:#ffffff;overflow:hidden;">
                  <tr>
                    <td style="padding:20px 20px 18px 20px;">
                      <div style="font-size:13px;letter-spacing:.08em;color:{category.accent_color};
                        font-weight:700;text-transform:uppercase;">TOP {index} · {html.escape(item.source)}</div>
                      <h2 style="margin:8px 0 10px 0;font-size:21px;line-height:1.35;color:#111827;">
                        {html.escape(item.title)}
                      </h2>
                      <p style="margin:0 0 16px 0;font-size:15px;line-height:1.75;color:#4b5563;">
                        {html.escape(summary)}
                      </p>
                      <table role="presentation" cellspacing="0" cellpadding="0" width="100%">
                        <tr>
                          <td style="font-size:13px;color:#6b7280;">
                            {html.escape(format_chinese_datetime(item.published_at))}
                          </td>
                          <td align="right">
                            <a href="{html.escape(item.link)}"
                              style="display:inline-block;padding:10px 16px;border-radius:999px;
                              background:{category.accent_color};color:#ffffff;text-decoration:none;
                              font-size:14px;font-weight:700;">阅读全文</a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            """
        )

    if cards:
        return "\n".join(cards)

    return f"""
    <tr>
      <td style="padding:0 24px 24px 24px;">
        <div style="border:1px dashed #cbd5e1;border-radius:18px;padding:22px;background:#ffffff;
          color:#475569;font-size:15px;line-height:1.8;">
          暂时没有抓取到可展示的新闻。请检查 RSS 网络访问，或稍后重新运行工作流。
        </div>
      </td>
    </tr>
    """


def build_html_email(category: NewsCategory, items: list[NewsItem], now: datetime) -> str:
    date_text = now.strftime("%Y年%m月%d日")
    cards_html = article_cards(items, category)
    preheader = html.escape(f"{category.title} · {date_text} · {len(items)} 条精选")

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(category.subject_prefix)}</title>
  </head>
  <body style="margin:0;padding:0;background:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
    'Microsoft YaHei',Arial,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{preheader}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef2f7;">
      <tr>
        <td align="center" style="padding:28px 12px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
            style="max-width:720px;background:{category.soft_color};border-radius:28px;overflow:hidden;
            box-shadow:0 22px 60px rgba(15,23,42,.14);">
            <tr>
              <td style="padding:0;">
                <img src="{html.escape(category.hero_image)}" alt="{html.escape(category.title)}"
                  width="720" style="display:block;width:100%;max-width:720px;height:260px;object-fit:cover;">
              </td>
            </tr>
            <tr>
              <td style="padding:28px 28px 22px 28px;background:linear-gradient(135deg,#111827,#1f2937);">
                <div style="display:inline-block;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.12);
                  color:#d1d5db;font-size:13px;">北京时间 {html.escape(now.strftime('%H:%M'))} 发送</div>
                <h1 style="margin:14px 0 10px 0;color:#ffffff;font-size:34px;line-height:1.18;">
                  {html.escape(category.subject_prefix)}
                </h1>
                <p style="margin:0;color:#d1d5db;font-size:16px;line-height:1.8;">
                  {html.escape(date_text)} · {html.escape(category.intro)}
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:22px 24px 8px 24px;">
                <div style="padding:16px 18px;border-radius:18px;background:#ffffff;color:#374151;
                  font-size:15px;line-height:1.8;border:1px solid rgba(17,24,39,.06);">
                  今日共整理 <strong style="color:{category.accent_color};">{len(items)}</strong> 条重点资讯。
                  邮件内容来自公开新闻 RSS 聚合，点击按钮可打开原始报道。
                </div>
              </td>
            </tr>
            {cards_html}
            <tr>
              <td style="padding:4px 28px 28px 28px;color:#6b7280;font-size:12px;line-height:1.7;text-align:center;">
                自动发送自 GitHub Actions · 如需调整主题或收件人，请修改 daily_news_email.py
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def build_text_email(category: NewsCategory, items: list[NewsItem], now: datetime) -> str:
    lines = [
        f"{category.subject_prefix} - {now.strftime('%Y年%m月%d日')}",
        "",
        category.intro,
        "",
    ]

    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. {item.title}",
                f"来源：{item.source}｜时间：{format_chinese_datetime(item.published_at)}",
                f"摘要：{item.summary or '点击链接查看完整报道。'}",
                f"链接：{item.link}",
                "",
            ]
        )

    if not items:
        lines.append("暂时没有抓取到可展示的新闻。")

    return "\n".join(lines)


def build_subject(category: NewsCategory, now: datetime) -> str:
    return f"【{category.subject_prefix}】{now.strftime('%Y年%m月%d日')} 中文图文速览"


def env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量：{name}")
    return value


def env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def smtp_config() -> dict[str, str | int | bool]:
    username = required_env("SMTP_USERNAME")
    return {
        "host": required_env("SMTP_HOST"),
        "port": int(env_or_default("SMTP_PORT", "587")),
        "username": username,
        "password": required_env("SMTP_PASSWORD"),
        "from_addr": env_or_default("SMTP_FROM", username),
        "from_name": env_or_default("SMTP_FROM_NAME", "每日中文新闻"),
        "recipient": env_or_default("SMTP_RECIPIENT", RECIPIENT),
        "use_ssl": env_bool("SMTP_USE_SSL", False),
        "use_tls": env_bool("SMTP_USE_TLS", True),
    }


def send_email(subject: str, text_body: str, html_body: str, config: dict[str, str | int | bool]) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{config['from_name']} <{config['from_addr']}>"
    message["To"] = str(config["recipient"])
    message.set_content(text_body, subtype="plain", charset="utf-8")
    message.add_alternative(html_body, subtype="html", charset="utf-8")

    context = ssl.create_default_context()
    if config["use_ssl"]:
        with smtplib.SMTP_SSL(str(config["host"]), int(config["port"]), context=context) as smtp:
            smtp.login(str(config["username"]), str(config["password"]))
            smtp.send_message(message)
        return

    with smtplib.SMTP(str(config["host"]), int(config["port"])) as smtp:
        smtp.ehlo()
        if config["use_tls"]:
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(str(config["username"]), str(config["password"]))
        smtp.send_message(message)


def selected_categories(keys: list[str] | None) -> tuple[NewsCategory, ...]:
    if not keys:
        return CATEGORIES

    category_by_key = {category.key: category for category in CATEGORIES}
    missing = [key for key in keys if key not in category_by_key]
    if missing:
        available = ", ".join(category_by_key)
        raise ValueError(f"未知分类：{', '.join(missing)}。可选分类：{available}")
    return tuple(category_by_key[key] for key in keys)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="每天发送 AI、美股、世界杯三封中文图文新闻邮件。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            必需环境变量：
              SMTP_HOST       SMTP 服务器地址
              SMTP_USERNAME   SMTP 用户名
              SMTP_PASSWORD   SMTP 密码或授权码

            常用可选环境变量：
              SMTP_PORT       默认 587
              SMTP_FROM       发件邮箱，默认 SMTP_USERNAME
              SMTP_RECIPIENT  收件邮箱，默认 w1057742284@gmail.com
            """
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="只抓取和渲染，不发送邮件。")
    parser.add_argument(
        "--category",
        action="append",
        choices=[category.key for category in CATEGORIES],
        help="只发送指定分类；可重复使用。默认发送全部三类。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(env_or_default("NEWS_ITEM_LIMIT", str(DEFAULT_ITEM_LIMIT))),
        help=f"每封邮件展示新闻条数，默认 {DEFAULT_ITEM_LIMIT}。",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.limit < 1:
        raise ValueError("--limit 必须大于 0")

    now = get_china_now()
    categories = selected_categories(args.category)
    config = None if args.dry_run else smtp_config()

    for category in categories:
        print(f"正在抓取 {category.title} ...", flush=True)
        items = fetch_category_news(category, args.limit)
        subject = build_subject(category, now)
        text_body = build_text_email(category, items, now)
        html_body = build_html_email(category, items, now)

        if args.dry_run:
            print("=" * 80)
            print(subject)
            print(text_body[:1200])
            print(f"HTML 长度：{len(html_body)} 字符")
            continue

        assert config is not None
        send_email(subject, text_body, html_body, config)
        print(f"已发送：{subject}", flush=True)
        time.sleep(2)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
