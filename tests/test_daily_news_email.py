import unittest
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import daily_news_email as news


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Sample News</title>
    <item>
      <title>人工智能公司发布新模型</title>
      <link>https://example.com/ai</link>
      <description><![CDATA[<p>这是一条<strong>中文</strong>新闻摘要。</p>]]></description>
      <source>示例媒体</source>
      <pubDate>Tue, 16 Jun 2026 01:00:00 GMT</pubDate>
      <media:thumbnail url="https://example.com/ai.jpg" />
    </item>
  </channel>
</rss>
""".encode("utf-8")


class DailyNewsEmailTests(unittest.TestCase):
    def test_parse_rss_extracts_text_and_image(self):
        items = news.parse_rss(SAMPLE_RSS, "https://example.com/fallback.jpg")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "人工智能公司发布新模型")
        self.assertEqual(items[0].summary, "这是一条中文新闻摘要。")
        self.assertEqual(items[0].source, "示例媒体")
        self.assertEqual(items[0].image_url, "https://example.com/ai.jpg")

    def test_parse_rss_uses_fallback_image(self):
        rss_without_image = SAMPLE_RSS.replace(
            b'<media:thumbnail url="https://example.com/ai.jpg" />', b""
        )

        items = news.parse_rss(rss_without_image, "https://example.com/fallback.jpg")

        self.assertEqual(items[0].image_url, "https://example.com/fallback.jpg")

    def test_build_message_has_plain_text_and_html_parts(self):
        category = news.CATEGORIES[0]
        items = news.parse_rss(SAMPLE_RSS, category.banner_image)
        generated_at = datetime(2026, 6, 16, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

        message = news.build_message(
            category=category,
            items=items,
            generated_at=generated_at,
            sender="sender@example.com",
            sender_name="每日新闻助手",
            recipients=["receiver@example.com"],
        )

        self.assertIsInstance(message, EmailMessage)
        self.assertIn("AI 新闻日报", message["Subject"])
        self.assertEqual(message["To"], "receiver@example.com")
        self.assertIsNotNone(message.get_body(preferencelist=("plain",)))
        html_body = message.get_body(preferencelist=("html",))
        self.assertIsNotNone(html_body)
        self.assertIn("阅读全文", html_body.get_content())


if __name__ == "__main__":
    unittest.main()
