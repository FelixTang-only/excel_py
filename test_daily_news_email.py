import unittest

from daily_news_email import (
    CATEGORIES,
    NewsItem,
    build_message,
    parse_rss_items,
    render_html_email,
)


SAMPLE_RSS = b"""\
<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <item>
      <title>OpenAI 发布新模型 - 示例新闻</title>
      <link>https://example.com/ai</link>
      <source url="https://example.com">示例新闻</source>
      <pubDate>Thu, 18 Jun 2026 01:00:00 GMT</pubDate>
      <description>&lt;p&gt;模型能力升级，产业应用继续扩展。&lt;/p&gt;</description>
    </item>
    <item>
      <title>美股三大指数收涨 - 财经媒体</title>
      <link>https://example.com/stocks</link>
      <pubDate>Thu, 18 Jun 2026 02:30:00 GMT</pubDate>
      <description>科技股带动市场风险偏好回升。</description>
    </item>
  </channel>
</rss>
"""


class DailyNewsEmailTest(unittest.TestCase):
    def test_parse_rss_items(self):
        items = parse_rss_items(SAMPLE_RSS, limit=2)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "OpenAI 发布新模型")
        self.assertEqual(items[0].source, "示例新闻")
        self.assertEqual(items[0].published, "06月18日 09:00")
        self.assertEqual(items[0].summary, "模型能力升级，产业应用继续扩展。")
        self.assertEqual(items[1].source, "财经媒体")

    def test_render_html_email_has_image_and_news_cards(self):
        category = CATEGORIES[0]
        item = NewsItem(
            title="AI 行业继续升温",
            link="https://example.com/news",
            source="示例来源",
            published="今日更新",
            summary="企业正在加速落地 AI 应用。",
        )

        html = render_html_email(category, [item])

        self.assertIn(category.hero_image, html)
        self.assertIn("AI 行业继续升温", html)
        self.assertIn("今日重点", html)

    def test_build_message_contains_plain_text_and_html(self):
        category = CATEGORIES[2]
        message = build_message(category, [], "sender@example.com", "to@example.com")

        self.assertEqual(message["From"], "sender@example.com")
        self.assertEqual(message["To"], "to@example.com")
        self.assertIn(category.subject, message["Subject"])
        self.assertTrue(message.is_multipart())


if __name__ == "__main__":
    unittest.main()
