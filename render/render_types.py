# render 模块类型定义

SUPPORTED_OUTPUT_FORMATS = ["markdown", "docx", "pdf"]
RENDER_STATUS = ["success", "failed", "skipped"]

# typeset-engine 可用主题
THEME_MAP = {
    "official_document": "cms",    # 公文类用 cms 主题
    "meeting_minutes": "ms",       # 会议纪要用 ms 主题
    "news_article": "cicc",        # 新闻稿用 cicc 主题
    "speech": "ms",                # 讲话稿用 ms 主题
    "work_summary": "cms",         # 总结用 cms 主题
    "work_report": "cms",          # 汇报材料用 cms 主题
}
