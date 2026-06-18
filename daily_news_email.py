#!/usr/bin/env python3
"""Send daily Chinese news digest emails.

The script fetches three RSS digests, renders polished HTML emails with
category imagery, and sends each category as a separate message.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import re
import smtplib
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable


DEFAULT_RECIPIENT = "w1057742284@gmail.com"
DEFAULT_LIMIT = 6
DEFAULT_TIMEOUT = 12


@dataclass(frozen=True)
class NewsCategory:
    key: str
    title: str
    subject: str
    query: str
    intro: str
    accent: str
    gradient_start: str
    gradient_end: str
    hero_image: str


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    source: str
    published: str
    summary: str


CATEGORIES: tuple[NewsCategory, ...] = (
    NewsCategory(
        key="ai",
        title="AI 新闻早报",
        subject="AI 新闻早报",
        query="人工智能 OR AI 最新 新闻",
        intro="聚焦人工智能、模型发布、产业应用与监管动态。",
        accent="#7c3aed",
        gradient_start="#312e81",
        gradient_end="#7c3aed",
        hero_image=(
            "https://images.unsplash.com/photo-1677442136019-21780ecad995"
            "?auto=format&fit=crop&w=1200&q=80"
        ),
    ),
    NewsCategory(
        key="us-stocks",
        title="美股新闻早报",
        subject="美股新闻早报",
        query="美股 纳斯达克 标普 道琼斯 财经 新闻",
        intro="跟踪美股指数、重点公司、宏观数据与市场情绪。",
        accent="#059669",
        gradient_start="#064e3b",
        gradient_end="#059669",
        hero_image=(
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3"
            "?auto=format&fit=crop&w=1200&q=80"
        ),
    ),
    NewsCategory(
        key="world-cup",
        title="世界杯新闻早报",
        subject="世界杯新闻早报",
        query="世界杯 足球 最新 新闻",
        intro="整理世界杯赛事、球队备战、赛程与国际足坛焦点。",
        accent="#dc2626",
        gradient_start="#7f1d1d",
        gradient_end="#dc2626",
        hero_image=(
            "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d"
            "?auto=format&fit=crop&w=1200&q=80"
        ),
    ),
)


def build_google_news_rss_url(query: str) -> str:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "hl": "zh-CN",
            "gl": "CN",
            "ceid": "CN:zh-Hans",
        }
    )
    return f"https://news.google.com/rss/search?{params}"


def fetch_rss(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_rss_items(feed_xml: bytes, limit: int = DEFAULT_LIMIT) -> list[NewsItem]:
    root = ET.fromstring(feed_xml)
    items: list[NewsItem] = []

    for item in root.findall("./channel/item"):
        raw_title = get_child_text(item, "title")
        title, fallback_source = split_google_news_title(raw_title)
        source = get_child_text(item, "source") or fallback_source or "新闻来源"
        link = get_child_text(item, "link")
        published = get_child_text(item, "pubDate")
        summary = clean_html_text(get_child_text(item, "description"))

        if not title or not link:
            continue

        items.append(
            NewsItem(
                title=title,
                link=link,
                source=source,
                published=format_pub_date(published),
                summary=summary,
            )
        )

        if len(items) >= limit:
            break

    return items


def get_child_text(element: ET.Element, tag: str) -> str:
    child = element.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def split_google_news_title(raw_title: str) -> tuple[str, str]:
    title = clean_html_text(raw_title)
    if " - " not in title:
        return title, ""

    headline, source = title.rsplit(" - ", 1)
    return headline.strip(), source.strip()


def clean_html_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def format_pub_date(raw_date: str) -> str:
    if not raw_date:
        return "今日更新"

    try:
        parsed = dt.datetime.strptime(raw_date, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        return raw_date

    beijing_time = parsed.replace(tzinfo=dt.timezone.utc).astimezone(
        dt.timezone(dt.timedelta(hours=8))
    )
    return beijing_time.strftime("%m月%d日 %H:%M")


def fetch_category_items(
    category: NewsCategory,
    limit: int = DEFAULT_LIMIT,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[NewsItem]:
    try:
        feed = fetch_rss(build_google_news_rss_url(category.query), timeout=timeout)
        return parse_rss_items(feed, limit=limit)
    except Exception as exc:  # pragma: no cover - runtime network diagnostics
        print(f"[warn] {category.title} RSS 获取失败：{exc}", file=sys.stderr)
        return []


def render_html_email(category: NewsCategory, items: Iterable[NewsItem]) -> str:
    item_list = list(items)
    generated_at = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime(
        "%Y年%m月%d日 %H:%M"
    )

    cards = "\n".join(render_news_card(category, item, index + 1) for index, item in enumerate(item_list))
    if not cards:
        cards = render_empty_card(category)

    return f"""\
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(category.title)}</title>
</head>
<body style="margin:0;background:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',Arial,sans-serif;color:#172033;">
  <div style="display:none;max-height:0;overflow:hidden;color:transparent;">{html.escape(category.intro)}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f7;padding:28px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="680" cellpadding="0" cellspacing="0" style="width:100%;max-width:680px;background:#ffffff;border-radius:24px;overflow:hidden;box-shadow:0 18px 48px rgba(15,23,42,.14);">
          <tr>
            <td style="background:linear-gradient(135deg,{category.gradient_start},{category.gradient_end});padding:30px 30px 22px;color:#ffffff;">
              <div style="font-size:13px;letter-spacing:2px;text-transform:uppercase;opacity:.82;">Daily News Digest</div>
              <h1 style="margin:10px 0 8px;font-size:32px;line-height:1.2;font-weight:800;">{html.escape(category.title)}</h1>
              <p style="margin:0;font-size:16px;line-height:1.65;opacity:.92;">{html.escape(category.intro)}</p>
              <p style="margin:18px 0 0;font-size:13px;opacity:.78;">生成时间：{generated_at}（北京时间）</p>
            </td>
          </tr>
          <tr>
            <td>
              <img src="{category.hero_image}" alt="{html.escape(category.title)}" width="680" style="display:block;width:100%;max-height:260px;object-fit:cover;border:0;">
            </td>
          </tr>
          <tr>
            <td style="padding:28px 30px 12px;background:#ffffff;">
              <div style="display:inline-block;padding:7px 12px;border-radius:999px;background:{category.accent}18;color:{category.accent};font-size:13px;font-weight:700;">今日重点</div>
            </td>
          </tr>
          <tr>
            <td style="padding:0 30px 30px;background:#ffffff;">
              {cards}
            </td>
          </tr>
          <tr>
            <td style="padding:18px 30px 28px;background:#f8fafc;color:#64748b;font-size:12px;line-height:1.6;text-align:center;">
              本邮件由 GitHub Actions 自动发送。新闻来自公开 RSS，点击标题可查看原文。
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def render_news_card(category: NewsCategory, item: NewsItem, index: int) -> str:
    summary = item.summary or "点击标题查看完整报道。"
    if len(summary) > 150:
        summary = f"{summary[:147]}..."

    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden;background:#ffffff;">
  <tr>
    <td style="width:58px;padding:18px 0 18px 18px;vertical-align:top;">
      <div style="width:38px;height:38px;border-radius:14px;background:{category.accent};color:#ffffff;text-align:center;line-height:38px;font-weight:800;font-size:16px;">{index}</div>
    </td>
    <td style="padding:18px 18px 18px 12px;vertical-align:top;">
      <a href="{html.escape(item.link, quote=True)}" style="color:#0f172a;text-decoration:none;font-size:18px;line-height:1.45;font-weight:800;">{html.escape(item.title)}</a>
      <p style="margin:10px 0 0;color:#475569;font-size:14px;line-height:1.7;">{html.escape(summary)}</p>
      <p style="margin:12px 0 0;color:#94a3b8;font-size:12px;line-height:1.4;">
        <span style="color:{category.accent};font-weight:700;">{html.escape(item.source)}</span>
        <span>&nbsp;&middot;&nbsp;{html.escape(item.published)}</span>
      </p>
    </td>
  </tr>
</table>
"""


def render_empty_card(category: NewsCategory) -> str:
    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;border:1px dashed #cbd5e1;border-radius:18px;background:#f8fafc;">
  <tr>
    <td style="padding:22px;color:#475569;font-size:15px;line-height:1.7;">
      今天暂时没有抓取到稳定的新闻条目。请稍后查看新闻源，或检查 GitHub Actions 运行日志。
      <div style="margin-top:10px;color:{category.accent};font-weight:700;">{html.escape(category.title)} 会在下次定时任务继续自动更新。</div>
    </td>
  </tr>
</table>
"""


def render_text_email(category: NewsCategory, items: Iterable[NewsItem]) -> str:
    lines = [
        category.title,
        category.intro,
        "",
    ]

    item_list = list(items)
    if not item_list:
        lines.append("今天暂时没有抓取到稳定的新闻条目。")
        return "\n".join(lines)

    for index, item in enumerate(item_list, 1):
        lines.extend(
            [
                f"{index}. {item.title}",
                f"来源：{item.source} · {item.published}",
                item.summary or "点击链接查看完整报道。",
                item.link,
                "",
            ]
        )

    return "\n".join(lines)


def build_message(
    category: NewsCategory,
    items: list[NewsItem],
    sender: str,
    recipient: str,
) -> EmailMessage:
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%m月%d日")
    message = EmailMessage()
    message["Subject"] = f"{today} {category.subject}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(render_text_email(category, items))
    message.add_alternative(render_html_email(category, items), subtype="html")
    return message


def send_messages(messages: Iterable[EmailMessage], config: dict[str, str]) -> None:
    host = config["host"]
    port = int(config["port"])
    username = config["username"]
    password = config["password"]
    use_tls = config["use_tls"].lower() not in {"0", "false", "no"}

    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
            smtp.login(username, password)
            for message in messages:
                smtp.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        if use_tls:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        smtp.login(username, password)
        for message in messages:
            smtp.send_message(message)


def smtp_config_from_env() -> dict[str, str]:
    host = os.environ.get("SMTP_HOST", "").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    missing = [
        name
        for name, value in (
            ("SMTP_HOST", host),
            ("SMTP_USERNAME", username),
            ("SMTP_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "缺少 SMTP 配置："
            + ", ".join(missing)
            + "。请在 GitHub 仓库 Secrets 中配置后再运行。"
        )

    return {
        "host": host,
        "port": os.environ.get("SMTP_PORT", "587").strip() or "587",
        "username": username,
        "password": password,
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").strip() or "true",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="每天发送 AI、美股、世界杯三封中文图文新闻邮件。"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只抓取和渲染邮件，不连接 SMTP 发送。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.environ.get("NEWS_ITEM_LIMIT", DEFAULT_LIMIT)),
        help="每封邮件展示的新闻条数。",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("NEWS_FEED_TIMEOUT", DEFAULT_TIMEOUT)),
        help="RSS 请求超时时间（秒）。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    recipient = os.environ.get("NEWS_RECIPIENT_EMAIL", DEFAULT_RECIPIENT).strip()
    dry_run = args.dry_run or os.environ.get("NEWS_EMAIL_DRY_RUN") == "1"
    config = None if dry_run else smtp_config_from_env()
    sender = (
        os.environ.get("SMTP_FROM", "").strip()
        or (config["username"] if config else "")
        or os.environ.get("SMTP_USERNAME", "").strip()
        or "daily-news@example.com"
    )

    prepared_messages: list[EmailMessage] = []
    for category in CATEGORIES:
        items = fetch_category_items(category, limit=args.limit, timeout=args.timeout)
        prepared_messages.append(build_message(category, items, sender, recipient))
        print(f"[ok] 已生成 {category.title}：{len(items)} 条新闻")

    if dry_run:
        for message in prepared_messages:
            print(f"[dry-run] {message['To']} <= {message['Subject']}")
        return 0

    send_messages(prepared_messages, config)
    print(f"[ok] 已向 {recipient} 分别发送 {len(prepared_messages)} 封新闻邮件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
