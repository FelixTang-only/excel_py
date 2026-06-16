#!/usr/bin/env python3
"""Fetch Chinese news digests and send three styled email newsletters."""

from __future__ import annotations

import argparse
import html
import os
import re
import smtplib
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.header import Header
from email.message import EmailMessage
from email.utils import formataddr, parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo


DEFAULT_RECIPIENT = "w1057742284@gmail.com"
TIMEZONE = ZoneInfo("Asia/Shanghai")
MAX_ITEMS = 6

NAMESPACES = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
}


@dataclass(frozen=True)
class NewsCategory:
    key: str
    display_name: str
    subject_prefix: str
    query: str
    accent: str
    accent_dark: str
    banner_image: str
    intro: str


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    published: str
    image_url: str


CATEGORIES: tuple[NewsCategory, ...] = (
    NewsCategory(
        key="ai",
        display_name="AI 新闻",
        subject_prefix="AI 新闻日报",
        query="人工智能 AI 大模型 科技 最新 新闻",
        accent="#7c3aed",
        accent_dark="#4c1d95",
        banner_image="https://dummyimage.com/1200x520/4c1d95/ffffff.png&text=AI+News",
        intro="精选人工智能、大模型、芯片与科技产业的最新动态。",
    ),
    NewsCategory(
        key="us-stocks",
        display_name="美股新闻",
        subject_prefix="美股新闻日报",
        query="美股 纳斯达克 标普 道琼斯 财报 最新 新闻",
        accent="#0f766e",
        accent_dark="#134e4a",
        banner_image="https://dummyimage.com/1200x520/134e4a/ffffff.png&text=US+Stock+News",
        intro="追踪美股三大指数、热门公司、财报与宏观市场消息。",
    ),
    NewsCategory(
        key="world-cup",
        display_name="世界杯新闻",
        subject_prefix="世界杯新闻日报",
        query="2026 世界杯 足球 最新 新闻",
        accent="#16a34a",
        accent_dark="#14532d",
        banner_image="https://dummyimage.com/1200x520/14532d/ffffff.png&text=World+Cup+News",
        intro="关注世界杯赛程、球队、球星与赛事筹备相关新闻。",
    ),
)


def build_feed_urls(query: str) -> list[str]:
    """Return Chinese RSS search feeds ordered by preference."""
    dated_query = f"{query} when:1d"
    google_query = urllib.parse.quote_plus(dated_query)
    bing_query = urllib.parse.quote_plus(query)
    return [
        "https://news.google.com/rss/search?"
        f"q={google_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "https://www.bing.com/news/search?"
        f"q={bing_query}&format=rss&setlang=zh-Hans&cc=CN",
    ]


def fetch_url(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def child_text(element: ET.Element, path: str) -> str:
    child = element.find(path, NAMESPACES)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def strip_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", value)
    return value.strip()


def truncate_text(value: str, length: int = 150) -> str:
    value = value.strip()
    if len(value) <= length:
        return value
    return value[: length - 1].rstrip() + "…"


def extract_image_url(item: ET.Element) -> str:
    for path in ("media:content", "media:thumbnail"):
        media = item.find(path, NAMESPACES)
        if media is not None and media.attrib.get("url"):
            return media.attrib["url"].strip()

    enclosure = item.find("enclosure")
    if enclosure is not None:
        enclosure_type = enclosure.attrib.get("type", "")
        if enclosure_type.startswith("image/") and enclosure.attrib.get("url"):
            return enclosure.attrib["url"].strip()

    searchable_html = " ".join(
        part
        for part in (
            child_text(item, "description"),
            child_text(item, "content:encoded"),
        )
        if part
    )
    match = re.search(r"""<img[^>]+src=["']([^"']+)["']""", searchable_html, re.I)
    if match:
        return html.unescape(match.group(1)).strip()
    return ""


def normalize_title(title: str) -> str:
    return re.sub(r"\W+", "", title, flags=re.UNICODE).lower()


def parse_rss(xml_bytes: bytes, fallback_image: str) -> list[NewsItem]:
    root = ET.fromstring(xml_bytes)
    items: list[NewsItem] = []
    for item in root.findall("./channel/item"):
        title = child_text(item, "title")
        link = child_text(item, "link")
        if not title or not link:
            continue

        summary = strip_html(child_text(item, "description"))
        source = child_text(item, "source") or child_text(item, "dc:creator") or "新闻来源"
        published = child_text(item, "pubDate")
        image_url = extract_image_url(item) or fallback_image
        items.append(
            NewsItem(
                title=title,
                link=link,
                summary=truncate_text(summary),
                source=source,
                published=published,
                image_url=image_url,
            )
        )
    return items


def fetch_category_items(
    category: NewsCategory, limit: int = MAX_ITEMS
) -> tuple[list[NewsItem], list[str]]:
    items: list[NewsItem] = []
    seen_titles: set[str] = set()
    errors: list[str] = []

    for feed_url in build_feed_urls(category.query):
        try:
            feed_items = parse_rss(fetch_url(feed_url), category.banner_image)
        except (ET.ParseError, TimeoutError, urllib.error.URLError, OSError) as exc:
            errors.append(f"{feed_url}: {exc}")
            continue

        for item in feed_items:
            normalized = normalize_title(item.title)
            if normalized in seen_titles:
                continue
            seen_titles.add(normalized)
            items.append(item)
            if len(items) >= limit:
                return items, errors

    return items[:limit], errors


def format_cn_datetime(value: datetime) -> str:
    weekdays = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
    return f"{value:%Y年%m月%d日} {weekdays[value.weekday()]} {value:%H:%M}"


def format_pub_date(pub_date: str) -> str:
    if not pub_date:
        return "时间未标注"
    try:
        parsed = parsedate_to_datetime(pub_date)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        return format_cn_datetime(parsed.astimezone(TIMEZONE))
    except (TypeError, ValueError, IndexError, OSError):
        return pub_date


def render_item_card(item: NewsItem, category: NewsCategory, index: int) -> str:
    title = html.escape(item.title)
    link = html.escape(item.link, quote=True)
    source = html.escape(item.source)
    summary = html.escape(item.summary or "点击阅读全文，查看完整报道。")
    published = html.escape(format_pub_date(item.published))
    image_url = html.escape(item.image_url or category.banner_image, quote=True)
    return f"""
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 18px;border-collapse:separate;border-spacing:0;background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;overflow:hidden;box-shadow:0 14px 35px rgba(15,23,42,0.08);">
        <tr>
          <td style="padding:0;">
            <img src="{image_url}" alt="{title}" width="640" style="display:block;width:100%;max-height:260px;object-fit:cover;border:0;">
          </td>
        </tr>
        <tr>
          <td style="padding:22px 24px 24px;">
            <div style="font-size:13px;letter-spacing:0.08em;color:{category.accent};font-weight:700;text-transform:uppercase;">{category.display_name} #{index}</div>
            <h2 style="margin:10px 0 10px;font-size:22px;line-height:1.35;color:#111827;font-weight:800;">
              <a href="{link}" style="color:#111827;text-decoration:none;">{title}</a>
            </h2>
            <p style="margin:0 0 18px;font-size:15px;line-height:1.8;color:#4b5563;">{summary}</p>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
              <tr>
                <td style="font-size:13px;color:#6b7280;">{source} · {published}</td>
                <td align="right">
                  <a href="{link}" style="display:inline-block;background:{category.accent};color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;padding:10px 16px;border-radius:999px;">阅读全文</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    """


def render_empty_state(category: NewsCategory) -> str:
    search_link = (
        "https://news.google.com/search?q="
        + urllib.parse.quote_plus(category.query)
        + "&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    )
    return f"""
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;">
        <tr>
          <td style="padding:28px;text-align:center;">
            <h2 style="margin:0 0 12px;color:#111827;">今天暂未获取到稳定的 RSS 新闻</h2>
            <p style="margin:0 0 18px;color:#4b5563;line-height:1.8;">可以稍后重试，或点击下方按钮查看实时搜索结果。</p>
            <a href="{html.escape(search_link, quote=True)}" style="display:inline-block;background:{category.accent};color:#ffffff;text-decoration:none;font-weight:700;padding:11px 18px;border-radius:999px;">查看实时新闻</a>
          </td>
        </tr>
      </table>
    """


def render_html_email(
    category: NewsCategory,
    items: Iterable[NewsItem],
    generated_at: datetime,
) -> str:
    item_list = list(items)
    cards = "\n".join(
        render_item_card(item, category, index)
        for index, item in enumerate(item_list, start=1)
    )
    if not cards:
        cards = render_empty_state(category)

    date_text = html.escape(format_cn_datetime(generated_at))
    intro = html.escape(category.intro)
    display_name = html.escape(category.display_name)
    banner = html.escape(category.banner_image, quote=True)
    preheader = html.escape(f"{display_name}已送达，共 {len(item_list)} 条精选新闻。")

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{display_name}</title>
  </head>
  <body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{preheader}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f4f6;border-collapse:collapse;">
      <tr>
        <td align="center" style="padding:30px 12px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;border-collapse:collapse;">
            <tr>
              <td style="border-radius:26px;overflow:hidden;background:{category.accent_dark};box-shadow:0 24px 60px rgba(15,23,42,0.18);">
                <img src="{banner}" alt="{display_name}" width="680" style="display:block;width:100%;height:auto;border:0;">
                <div style="padding:30px 30px 34px;background:linear-gradient(135deg,{category.accent_dark},#111827);">
                  <div style="display:inline-block;background:rgba(255,255,255,0.14);border:1px solid rgba(255,255,255,0.22);color:#ffffff;border-radius:999px;padding:8px 14px;font-size:13px;font-weight:700;">每日 09:00 中文新闻</div>
                  <h1 style="margin:18px 0 12px;color:#ffffff;font-size:34px;line-height:1.2;font-weight:900;">{display_name}</h1>
                  <p style="margin:0;color:#e5e7eb;font-size:16px;line-height:1.8;">{intro}</p>
                  <p style="margin:16px 0 0;color:#cbd5e1;font-size:13px;">生成时间：{date_text}</p>
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:22px 0 0;">
                {cards}
              </td>
            </tr>
            <tr>
              <td style="padding:10px 4px 0;text-align:center;color:#6b7280;font-size:12px;line-height:1.7;">
                本邮件由自动化脚本根据公开新闻 RSS 生成，新闻版权归原媒体所有。
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def render_text_email(
    category: NewsCategory, items: Iterable[NewsItem], generated_at: datetime
) -> str:
    lines = [
        category.display_name,
        category.intro,
        f"生成时间：{format_cn_datetime(generated_at)}",
        "",
    ]
    item_list = list(items)
    if not item_list:
        lines.append("今天暂未获取到稳定的 RSS 新闻，请稍后查看实时新闻。")
    for index, item in enumerate(item_list, start=1):
        lines.extend(
            [
                f"{index}. {item.title}",
                f"来源：{item.source} · {format_pub_date(item.published)}",
                item.summary or "点击链接阅读全文。",
                item.link,
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def build_message(
    category: NewsCategory,
    items: list[NewsItem],
    generated_at: datetime,
    sender: str,
    sender_name: str,
    recipients: list[str],
) -> EmailMessage:
    message = EmailMessage()
    date_suffix = generated_at.strftime("%Y-%m-%d")
    message["Subject"] = f"{category.subject_prefix}｜{date_suffix}"
    message["From"] = formataddr((str(Header(sender_name, "utf-8")), sender))
    message["To"] = ", ".join(recipients)
    message.set_content(render_text_email(category, items, generated_at))
    message.add_alternative(
        render_html_email(category, items, generated_at), subtype="html"
    )
    return message


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def split_recipients(raw: str) -> list[str]:
    recipients = [value.strip() for value in re.split(r"[,;]", raw) if value.strip()]
    if not recipients:
        raise ValueError("至少需要配置一个收件人")
    return recipients


def load_recipients(cli_recipients: list[str] | None) -> list[str]:
    if cli_recipients:
        return cli_recipients
    raw = os.getenv("NEWS_RECIPIENTS") or os.getenv("NEWS_RECIPIENT") or DEFAULT_RECIPIENT
    return split_recipients(raw)


def send_messages(messages: list[EmailMessage]) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        raise RuntimeError("缺少 SMTP_HOST 环境变量，无法发送邮件")

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    use_ssl = env_flag("SMTP_USE_SSL", False)
    use_tls = env_flag("SMTP_USE_TLS", True)

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_class(smtp_host, smtp_port, timeout=30) as smtp:
        if not use_ssl and use_tls:
            smtp.starttls()
        if smtp_username and smtp_password:
            smtp.login(smtp_username, smtp_password)
        for message in messages:
            smtp.send_message(message)


def write_previews(messages: list[EmailMessage], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for message in messages:
        subject = str(message["Subject"]).replace("/", "-").replace("｜", "-")
        safe_name = re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", subject).strip("_")
        html_part = message.get_body(preferencelist=("html",))
        text_part = message.get_body(preferencelist=("plain",))
        if html_part is not None:
            (output_dir / f"{safe_name}.html").write_text(
                html_part.get_content(), encoding="utf-8"
            )
        if text_part is not None:
            (output_dir / f"{safe_name}.txt").write_text(
                text_part.get_content(), encoding="utf-8"
            )


def selected_categories(keys: list[str] | None) -> list[NewsCategory]:
    if not keys:
        return list(CATEGORIES)
    category_map = {category.key: category for category in CATEGORIES}
    return [category_map[key] for key in keys]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="发送每日中文新闻邮件")
    parser.add_argument("--dry-run", action="store_true", help="只生成邮件预览，不发送")
    parser.add_argument(
        "--output-dir",
        default="news_previews",
        help="dry-run 预览输出目录，默认 news_previews",
    )
    parser.add_argument(
        "--limit", type=int, default=MAX_ITEMS, help=f"每封邮件新闻数量，默认 {MAX_ITEMS}"
    )
    parser.add_argument(
        "--recipient",
        action="append",
        help="收件人邮箱；可重复传入。默认使用 NEWS_RECIPIENTS/NEWS_RECIPIENT 或内置邮箱",
    )
    parser.add_argument(
        "--category",
        action="append",
        choices=[category.key for category in CATEGORIES],
        help="仅处理指定分类；可重复传入",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    generated_at = datetime.now(TIMEZONE)
    recipients = load_recipients(args.recipient)
    sender = os.getenv("SMTP_FROM") or os.getenv("SMTP_USERNAME") or "news@example.com"
    sender_name = os.getenv("SMTP_FROM_NAME", "每日新闻助手")

    messages: list[EmailMessage] = []
    for category in selected_categories(args.category):
        items, errors = fetch_category_items(category, max(1, args.limit))
        for error in errors:
            print(f"[warn] {category.key} RSS 获取失败：{error}", file=sys.stderr)
        messages.append(
            build_message(category, items, generated_at, sender, sender_name, recipients)
        )

    if args.dry_run:
        output_dir = Path(args.output_dir)
        write_previews(messages, output_dir)
        print(f"已生成 {len(messages)} 封邮件预览：{output_dir.resolve()}")
        return 0

    send_messages(messages)
    print(f"已发送 {len(messages)} 封新闻邮件到：{', '.join(recipients)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
