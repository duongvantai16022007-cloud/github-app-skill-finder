import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
import requests
from pydantic import BaseModel

from models import (
    BatchEvaluationResult,
    RepoCandidate,
    RepoEvaluation,
    SearchPlan,
)

T = TypeVar("T", bound=BaseModel)


FREE_AI_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "smart_zerokey": {
        "label": "⚡ Free No-API-Key Mode (Smart Hybrid AI - Zero Config)",
        "label_vi": "⚡ Miễn phí Không cần API Key (Smart Hybrid AI - Không bao giờ lỗi)",
        "base_url": "https://text.pollinations.ai/openai",
        "env_key": "",
        "requires_key": False,
        "help_url": "",
        "models": [
            "hybrid-auto (Cloud AI + Smart NLP Auto-Fallback)",
            "local-smart-nlp (Ultra-Fast < 2s - Direct README/SKILL.md Analyzer)",
            "openai-fast",
        ],
    },
    "glm_bigmodel": {
        "label": "🟢 Zhipu AI / GLM (Free API: glm-4-flash, glm-z1-flash)",
        "label_vi": "🟢 Zhipu AI / GLM (Free API: glm-4-flash, glm-z1-flash)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "env_key": "GLM_API_KEY",
        "requires_key": True,
        "help_url": "https://open.bigmodel.cn/usercenter/apikeys",
        "models": [
            "glm-4-flash",
            "glm-z1-flash",
            "glm-4-flash-250414",
            "glm-4.5-flash",
        ],
    },
    "openrouter_free": {
        "label": "🌐 OpenRouter (Free Models: GLM, DeepSeek, Qwen, Llama)",
        "label_vi": "🌐 OpenRouter (Model :free — GLM, DeepSeek, Qwen, Llama)",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "env_key": "OPENROUTER_API_KEY",
        "requires_key": True,
        "help_url": "https://openrouter.ai/keys",
        "models": [
            "z-ai/glm-4.5-air:free",
            "thudm/glm-4-9b:free",
            "deepseek/deepseek-chat-v3-0324:free",
            "deepseek/deepseek-r1:free",
            "qwen/qwen-2.5-72b-instruct:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-3-27b-it:free",
        ],
    },
    "groq_free": {
        "label": "🚀 Groq Cloud (Fast Free Tier)",
        "label_vi": "🚀 Groq Cloud (Free Tier tốc độ cao)",
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "env_key": "GROQ_API_KEY",
        "requires_key": True,
        "help_url": "https://console.groq.com/keys",
        "models": [
            "llama-3.3-70b-versatile",
            "qwen-qwq-32b",
            "gemma2-9b-it",
            "llama-3.1-8b-instant",
        ],
    },
    "ollama_local": {
        "label": "💻 Ollama Local (Run GLM-4 / Qwen / Llama locally)",
        "label_vi": "💻 Ollama Local (Chạy GLM-4 / Qwen / Llama miễn phí trên máy)",
        "base_url": "http://localhost:11434/v1/chat/completions",
        "env_key": "",
        "requires_key": False,
        "help_url": "https://ollama.com",
        "models": [
            "glm4:latest",
            "qwen2.5:latest",
            "llama3.2:latest",
            "deepseek-r1:latest",
        ],
    },
    "gemini": {
        "label": "✨ Google Gemini (AI Studio Free Tier)",
        "label_vi": "✨ Google Gemini (AI Studio Free Tier)",
        "base_url": "gemini-sdk",
        "env_key": "GEMINI_API_KEY",
        "requires_key": True,
        "help_url": "https://aistudio.google.com/apikey",
        "models": [
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-pro-preview",
        ],
    },
    "custom_openai": {
        "label": "🔧 Custom (Any OpenAI-Compatible Endpoint)",
        "label_vi": "🔧 Tùy chỉnh (OpenAI-Compatible Endpoint bất kỳ)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "env_key": "CUSTOM_API_KEY",
        "requires_key": False,
        "help_url": "",
        "models": ["glm-4-flash"],
    },
}


class SmartZeroKeyEngine:
    """Built-in NLP & Markdown/SKILL.md structural analyzer (100% free, zero API keys, zero rate limits)."""

    # (triggers, english_queries, label_en, label_vi)
    CONCEPT_MAP: List[Tuple[List[str], List[str], str, str]] = [
        (["expense", "finance", "budget", "chi tiêu", "tài chính", "ngân sách", "thu chi"], ["expense tracker", "personal finance", "budget app"], "Personal Finance & Expense Tracking", "Quản lý chi tiêu & tài chính cá nhân"),
        (["note", "markdown", "knowledge", "obsidian", "ghi chú", "nhật ký"], ["markdown note", "note taking app", "knowledge base"], "Markdown Note-Taking & Knowledge Base", "Ghi chú & quản lý kiến thức Markdown"),
        (["video downloader", "youtube", "yt-dlp", "tải video", "tiktok"], ["video downloader gui", "yt-dlp gui", "youtube downloader"], "Multi-Platform Video Downloader", "Tải video đa nền tảng (YouTube / Social)"),
        (["ebook", "epub", "pdf reader", "book reader", "đọc sách", "thư viện sách"], ["ebook reader", "epub reader", "pdf reader desktop"], "E-Book & PDF Reader", "Đọc và quản lý sách điện tử (EPUB / PDF)"),
        (["todo", "kanban", "task manager", "project management", "công việc", "quản lý dự án"], ["task manager", "kanban board", "todo app"], "Task & Kanban Management", "Quản lý công việc (Todo / Kanban)"),
        (["browser", "playwright", "selenium", "scrape", "scraper", "screenshot", "trình duyệt", "cào dữ liệu", "chụp ảnh màn hình"], ["playwright browser", "browser automation", "web scraping"], "Browser Automation & UI Testing", "Tự động hóa trình duyệt & Kiểm thử UI"),
        (["document", "word", "docx", "excel", "xlsx", "pdf", "ocr", "tài liệu", "bảng biểu"], ["pdf docx", "document processing", "office document"], "Document Processing (PDF / Word / Excel)", "Xử lý tài liệu (PDF / Word / Excel)"),
        (["security", "audit", "vulnerability", "code review", "pull request", "bảo mật", "lỗ hổng"], ["security audit", "code review", "vulnerability scanner"], "Security Audit & Code Review", "Kiểm tra bảo mật (Security Audit) & Code Review"),
        (["frontend", "ui/ux", "ui design", "tailwind", "component", "giao diện", "thiết kế"], ["frontend design", "react tailwind", "ui components"], "Frontend UI/UX Design & Components", "Thiết kế giao diện Frontend & UI/UX"),
        (["music", "audio", "spotify", "mp3", "podcast", "nghe nhạc"], ["music player", "audio player", "spotify client"], "Music & Audio Player", "Trình phát nhạc & âm thanh"),
        (["translate", "translator", "dictionary", "dịch", "từ điển"], ["translator app", "translation tool", "dictionary"], "Translation & Language Tool", "Dịch thuật & Ngôn ngữ"),
        (["password", "2fa", "authenticator", "mật khẩu"], ["password manager", "authenticator app"], "Password Manager & Authentication", "Quản lý mật khẩu & Bảo mật"),
        (["chat", "chatbot", "llm", "ai client", "trò chuyện"], ["ai chat client", "llm desktop", "chat ui"], "AI Chat Client & LLM Interface", "Giao diện tương tác AI / Chatbot"),
        (["database", "sql", "postgres", "mysql", "sqlite", "cơ sở dữ liệu"], ["database client", "sql gui", "postgres tool"], "Database Management & SQL Client", "Quản trị và truy vấn Cơ sở dữ liệu"),
        (["test", "unit test", "e2e", "qa", "kiểm thử"], ["automated testing", "test generator", "e2e testing"], "Automated Software Testing", "Kiểm thử phần mềm tự động"),
    ]

    TECH_KEYWORDS = [
        "flutter", "react", "vue", "svelte", "nextjs", "electron", "tauri",
        "python", "typescript", "javascript", "rust", "go", "golang", "java",
        "kotlin", "swift", "dart", "docker", "playwright", "tailwind", "fastapi",
        "streamlit", "gradio", "langchain", "autogen", "crewai", "offline", "gui", "cli",
    ]

    @classmethod
    def build_plan(
        cls,
        user_requirement: str,
        search_mode: str = "app",
        preferred_language: Optional[str] = None,
        output_lang: str = "en",
    ) -> SearchPlan:
        is_en = output_lang == "en"
        text_lower = user_requirement.lower()
        matched_en_terms: List[str] = []
        extracted_features: List[str] = []
        detected_techs: List[str] = []

        for triggers, en_queries, label_en, label_vi in cls.CONCEPT_MAP:
            if any(t in text_lower for t in triggers):
                extracted_features.append(label_en if is_en else label_vi)
                for eq in en_queries:
                    if eq not in matched_en_terms:
                        matched_en_terms.append(eq)

        for tech in cls.TECH_KEYWORDS:
            if re.search(rf"\b{re.escape(tech)}\b", text_lower):
                detected_techs.append(tech)
                extracted_features.append(
                    f"Tech Stack / Platform: {tech.capitalize()}"
                    if is_en
                    else f"Công nghệ / Nền tảng: {tech.capitalize()}"
                )

        ascii_words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{2,}\b", user_requirement)
        stopwords = {
            "tim", "app", "ung", "dung", "cho", "voi", "cua", "cac", "mot", "nhung",
            "tren", "github", "skill", "skills", "agent", "agents", "the", "and",
            "for", "with", "find", "search", "build", "create", "that", "support", "supports",
        }
        en_tokens = [w.lower() for w in ascii_words if w.lower() not in stopwords]

        if not matched_en_terms:
            if en_tokens:
                matched_en_terms.append(" ".join(en_tokens[:4]))
            else:
                matched_en_terms.append("open source app" if search_mode == "app" else "claude agent skills")

        if not extracted_features:
            extracted_features = (
                ["Matches core functional requirements", "Open-source with clear documentation"]
                if is_en
                else ["Đáp ứng đúng chức năng mô tả", "Mã nguồn mở có tài liệu rõ ràng"]
            )

        queries: List[str] = []
        skill_keywords: List[str] = []

        if search_mode == "skill":
            extracted_features.insert(
                0,
                "AI Agent Integration (SKILL.md / MCP / Tool)"
                if is_en
                else "Tích hợp cho AI Agent (SKILL.md / MCP / Tool)",
            )
            base_kw = matched_en_terms[0].split()[0] if matched_en_terms else "automation"
            second_kw = matched_en_terms[0] if matched_en_terms else "coding"

            queries.append(f"{second_kw} agent skill")
            queries.append(f"{base_kw} claude skill")
            queries.append(f"{second_kw} mcp server")
            queries.append("agent skills SKILL.md")

            for term in matched_en_terms[:2]:
                for w in term.split():
                    if len(w) >= 3 and w not in skill_keywords:
                        skill_keywords.append(w)
            for t in detected_techs[:2]:
                if t not in skill_keywords:
                    skill_keywords.append(t)
            if not skill_keywords:
                skill_keywords = ["skill", "agent", "mcp"]
        else:
            tech_str = " ".join(detected_techs[:2])
            for term in matched_en_terms[:3]:
                q = f"{term} {tech_str}".strip() if tech_str and tech_str not in term else term
                if q not in queries:
                    queries.append(q)
            if len(queries) == 1 and len(matched_en_terms) > 1:
                queries.append(matched_en_terms[1])

        if preferred_language and preferred_language not in ("All", "Tất cả"):
            queries = [
                f"{q} language:{preferred_language}" if "language:" not in q.lower() else q
                for q in queries
            ]

        if is_en:
            mode_prefix = "Find AI Agent Skills (SKILL.md / MCP)" if search_mode == "skill" else "Find Open-Source GitHub Apps"
            intent_summary = f"{mode_prefix} matching: {user_requirement.strip()}"
        else:
            mode_prefix = "Tìm kiếm Kỹ năng AI Agent (SKILL.md / MCP)" if search_mode == "skill" else "Tìm kiếm Ứng dụng mã nguồn mở"
            intent_summary = f"{mode_prefix} theo yêu cầu: {user_requirement.strip()}"

        return SearchPlan(
            intent_summary=intent_summary,
            extracted_features=extracted_features[:6],
            target_language=preferred_language if preferred_language not in ("All", "Tất cả") else None,
            github_queries=queries[:4],
            skill_keywords=skill_keywords[:5],
        )

    @classmethod
    def evaluate_candidates(
        cls,
        user_requirement: str,
        search_plan: SearchPlan,
        candidates: List[RepoCandidate],
        search_mode: str = "app",
        output_lang: str = "en",
    ) -> List[RepoEvaluation]:
        is_en = output_lang == "en"
        target_tokens = set()
        for q in search_plan.github_queries:
            for w in re.findall(r"[a-zA-Z0-9+#-]+", q.lower()):
                if not w.startswith("language:") and len(w) >= 3:
                    target_tokens.add(w)
        for kw in search_plan.skill_keywords:
            target_tokens.add(kw.lower())
        for w in re.findall(r"[a-zA-Z0-9+#-]+", user_requirement.lower()):
            if len(w) >= 3:
                target_tokens.add(w)

        evaluations: List[RepoEvaluation] = []

        for c in candidates:
            combined_doc = f"{c.full_name} {c.description} {' '.join(c.topics)} {c.skill_md_excerpt} {c.readme_excerpt}".lower()

            matched_kws = [kw for kw in target_tokens if kw in combined_doc]
            kw_ratio = len(matched_kws) / max(1, len(target_tokens))
            kw_score = min(50, int(round(kw_ratio * 50)) + 15)

            doc_score = 10
            is_awesome_or_list = bool(
                re.search(r"\b(awesome|curated-list|roadmap|interview)\b", c.full_name.lower())
            )
            is_actual_app = not is_awesome_or_list

            if search_mode == "skill":
                if c.skill_paths:
                    doc_score += 20
                    is_actual_app = True
                elif "mcp" in combined_doc or "model context protocol" in combined_doc or "skill" in combined_doc:
                    doc_score += 14
                    is_actual_app = True
            else:
                if is_actual_app:
                    doc_score += 12
                if len(c.readme_excerpt) > 800:
                    doc_score += 8

            star_score = min(14, int(math.log10(max(1, c.stars)) * 3.5))
            recency_score = 6 if c.updated_at >= "2025" else (3 if c.updated_at >= "2024" else 1)

            total_score = max(35, min(98, kw_score + doc_score + star_score + recency_score))

            compatible_agents: List[str] = []
            if search_mode == "skill":
                if len(c.skill_paths) > 1:
                    category_badge = "🗂️ Skill Pack" if is_en else "🗂️ Bộ sưu tập Skills (Skill Pack)"
                elif len(c.skill_paths) == 1:
                    category_badge = "🧩 Standard SKILL.md" if is_en else "🧩 SKILL.md Chuẩn"
                elif "mcp" in combined_doc or "modelcontextprotocol" in combined_doc:
                    category_badge = "🔌 MCP Server / Tool" if is_en else "🔌 MCP Server / Agent Tool"
                else:
                    category_badge = "📜 Agent Rules / Workflow"

                compatible_agents = ["Antigravity", "Claude Code", "Cursor", "Cline"]
                if "mcp" in combined_doc:
                    compatible_agents.append("MCP Clients")
            else:
                if not is_actual_app:
                    category_badge = "📚 Curated List / Docs" if is_en else "📚 Danh sách / Tài liệu"
                elif any(x in combined_doc for x in ["docker-compose", "self-hosted", "web app", "nextjs"]):
                    category_badge = "🌐 Web App / Self-hosted"
                elif any(x in combined_doc for x in ["cli", "command-line", "terminal"]):
                    category_badge = "🛠️ CLI Tool" if is_en else "🛠️ Công cụ CLI"
                else:
                    category_badge = "📦 Complete App" if is_en else "📦 Ứng dụng hoàn chỉnh"

            extracted_bullets = cls._extract_bullets(c.skill_md_excerpt or c.readme_excerpt)
            if not extracted_bullets:
                if is_en:
                    extracted_bullets = [f"Topic: #{t}" for t in c.topics[:4]] or [
                        f"Built primarily with {c.language}",
                        "Open-source repository with documentation on GitHub",
                    ]
                else:
                    extracted_bullets = [f"Chủ đề: #{t}" for t in c.topics[:4]] or [
                        f"Phát triển bằng ngôn ngữ {c.language}",
                        "Cung cấp mã nguồn mở và hướng dẫn trên GitHub",
                    ]

            quick_start = cls._extract_quick_start(c, search_mode=search_mode, is_en=is_en)
            summary_text = cls._build_summary(c, search_mode=search_mode, is_en=is_en)

            matching_reasons = []
            if matched_kws:
                matching_reasons.append(
                    f"Directly matches technical keywords in documentation: {', '.join(sorted(matched_kws)[:8])}."
                    if is_en
                    else f"Khớp trực tiếp các từ khóa kỹ thuật trong tài liệu: {', '.join(sorted(matched_kws)[:8])}."
                )
            if search_mode == "skill" and c.skill_paths:
                matching_reasons.append(
                    f"Contains {len(c.skill_paths)} direct skill definition file(s) ({', '.join(c.skill_paths[:3])})."
                    if is_en
                    else f"Phát hiện trực tiếp {len(c.skill_paths)} file định nghĩa kỹ năng ({', '.join(c.skill_paths[:3])}) trong repository."
                )
            if c.stars >= 100:
                matching_reasons.append(
                    f"Well-regarded by the community with {c.stars:,} ⭐ and {c.forks:,} forks."
                    if is_en
                    else f"Được cộng đồng đánh giá cao với {c.stars:,} ⭐ và {c.forks:,} bản fork."
                )
            if not matching_reasons:
                matching_reasons.append(
                    "Matches GitHub Search API query criteria."
                    if is_en
                    else "Khớp với truy vấn tìm kiếm trên GitHub Search API."
                )

            caveats = []
            if c.updated_at and c.updated_at < "2024-01-01":
                caveats.append(
                    f"Last updated on {c.updated_at}; verify compatibility with latest dependencies."
                    if is_en
                    else f"Lần cập nhật gần nhất từ {c.updated_at}, cần kiểm tra tính tương thích mới nhất."
                )
            if search_mode == "skill" and not c.skill_paths:
                caveats.append(
                    "No standalone SKILL.md at root; integrate via MCP config or README instructions."
                    if is_en
                    else "Không có file SKILL.md riêng lẻ ở gốc; cần tích hợp qua cấu hình MCP hoặc hướng dẫn trong README."
                )
            if not is_actual_app and search_mode == "app":
                caveats.append(
                    "This appears to be a curated list or library rather than a standalone end-user application."
                    if is_en
                    else "Đây có thể là danh sách tổng hợp (awesome-list) hoặc thư viện thay vì ứng dụng cài đặt trực tiếp."
                )
            if not caveats:
                caveats.append(
                    f"Review license ({c.license_name}) and environment prerequisites before deployment."
                    if is_en
                    else f"Kiểm tra kỹ giấy phép ({c.license_name}) và yêu cầu môi trường trước khi cài đặt."
                )

            evaluations.append(
                RepoEvaluation(
                    full_name=c.full_name,
                    match_score=total_score,
                    is_actual_app=is_actual_app,
                    category_badge=category_badge,
                    compatible_agents=compatible_agents,
                    summary_vi=summary_text,
                    key_features=extracted_bullets[:5],
                    matching_reasons=matching_reasons,
                    missing_or_caveats=caveats,
                    quick_start=quick_start,
                )
            )

        return evaluations

    @staticmethod
    def _extract_bullets(markdown_text: str) -> List[str]:
        bullets: List[str] = []
        for line in markdown_text.splitlines():
            s = line.strip()
            if s.startswith(("- ", "* ")) and 12 < len(s) < 160:
                clean_line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s[2:]).strip()
                clean_line = re.sub(r"[`*_~]", "", clean_line).strip()
                if clean_line and not clean_line.lower().startswith(("table of contents", "license", "contributing")):
                    bullets.append(clean_line)
            if len(bullets) >= 5:
                break
        return bullets

    @staticmethod
    def _extract_quick_start(c: RepoCandidate, search_mode: str = "app", is_en: bool = True) -> str:
        text = f"{c.skill_md_excerpt}\n{c.readme_excerpt}"
        cmd_patterns = [
            r"((?:npx|npm install|pnpm add|pip install|uvx|docker run|docker compose up|brew install|cargo install|flutter pub)[^\n`\"']+)",
        ]
        for pat in cmd_patterns:
            m = re.search(pat, text)
            if m:
                cmd = m.group(1).strip()
                if 8 <= len(cmd) <= 120:
                    return cmd

        if search_mode == "skill":
            if c.skill_paths:
                first_skill = c.skill_paths[0]
                comment = (
                    f"# Copy skill file ({first_skill}) to ~/.gemini/antigravity/skills/ or .claude/skills/"
                    if is_en
                    else f"# Copy file kỹ năng ({first_skill}) vào ~/.gemini/antigravity/skills/ hoặc .claude/skills/"
                )
                return f"git clone {c.html_url}.git\n{comment}"
            return f"git clone {c.html_url}.git"

        return f"git clone {c.html_url}.git"

    @staticmethod
    def _build_summary(c: RepoCandidate, search_mode: str = "app", is_en: bool = True) -> str:
        desc = c.description.strip() if c.description else (
            "Open-source project on GitHub" if is_en else "Dự án mã nguồn mở trên GitHub"
        )
        if search_mode == "skill":
            if c.skill_md_excerpt:
                fm_match = re.search(r"description:\s*(.+)", c.skill_md_excerpt)
                if fm_match:
                    skill_desc = fm_match.group(1).strip().strip("\"'")
                    if len(skill_desc) > 15:
                        desc = skill_desc
            if is_en:
                skill_note = f" (Includes {len(c.skill_paths)} SKILL.md definition file(s))" if c.skill_paths else ""
                return f"{desc}{skill_note}. Primary language: {c.language}, with {c.stars:,} stars on GitHub."
            skill_note = f" (Bao gồm {len(c.skill_paths)} file định nghĩa kỹ năng SKILL.md)" if c.skill_paths else ""
            return f"{desc}{skill_note}. Ngôn ngữ chính: {c.language}, đạt {c.stars:,} sao trên GitHub."

        if is_en:
            return f"{desc}. Developed in {c.language}, with {c.stars:,} stars and last updated on {c.updated_at}."
        return f"{desc}. Dự án được phát triển bằng {c.language}, hiện có {c.stars:,} sao và cập nhật lần cuối ngày {c.updated_at}."


class GitHubAIAdvisor:
    """Multi-provider AI Engine (Smart Hybrid Zero-Key, GLM Free, OpenRouter Free, Groq, Ollama, Gemini)
    supporting both App Search and AI Agent Skill Search (SKILL.md / MCP) in English and Vietnamese.
    """

    def __init__(
        self,
        provider_key: str = "smart_zerokey",
        model_name: str = "hybrid-auto (Cloud AI + Smart NLP Auto-Fallback)",
        api_key: Optional[str] = None,
        custom_base_url: Optional[str] = None,
        output_lang: str = "en",
    ):
        self.provider_key = (
            provider_key if provider_key in FREE_AI_PROVIDERS else "smart_zerokey"
        )
        self.provider_info = FREE_AI_PROVIDERS[self.provider_key]
        self.model_name = model_name.strip() if model_name else self.provider_info["models"][0]
        self.api_key = (api_key or "").strip()
        self.base_url = (
            custom_base_url.strip()
            if custom_base_url and custom_base_url.strip()
            else self.provider_info["base_url"]
        )
        self.output_lang = output_lang if output_lang in ("en", "vi") else "en"

    def _call_llm_json(
        self,
        system_instruction: str,
        user_prompt: str,
        schema_cls: Type[T],
        example_json: Dict[str, Any],
    ) -> T:
        if self.provider_key == "gemini":
            from google import genai

            client = genai.Client(api_key=self.api_key)
            interaction = client.interactions.create(
                model=self.model_name,
                system_instruction=system_instruction,
                input=user_prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema_cls.model_json_schema(),
                },
            )
            return schema_cls.model_validate_json(interaction.output_text)

        example_str = json.dumps(example_json, ensure_ascii=False, indent=2)
        full_system = (
            f"{system_instruction}\n\n"
            "IMPORTANT: Return ONLY a valid JSON object (no surrounding explanation text) "
            f"following this exact JSON structure:\n{example_str}"
        )

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GitHub-App-And-Skill-Finder/2.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.provider_key == "openrouter_free":
            headers["HTTP-Referer"] = "https://github.com"
            headers["X-Title"] = "GitHub App & Agent Skill Finder"

        target_model = self.model_name
        if self.provider_key == "smart_zerokey":
            target_model = "openai-fast"

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": full_system},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        is_reasoning_model = any(
            tag in target_model.lower()
            for tag in ["z1", "r1", "qwq", "think", "openai-fast", "gpt-oss"]
        )
        if not is_reasoning_model and self.provider_key in ("glm_bigmodel", "groq_free"):
            payload["response_format"] = {"type": "json_object"}

        timeout_sec = 25 if self.provider_key == "smart_zerokey" else 90
        resp = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=timeout_sec,
        )

        if resp.status_code != 200:
            error_detail = resp.text[:400]
            raise RuntimeError(
                f"API Error ({self.provider_info['label']} - HTTP {resp.status_code}): {error_detail}"
            )

        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"Empty choices in AI response: {data}")

        message = choices[0].get("message") or {}
        raw_content = (
            message.get("content")
            or message.get("reasoning_content")
            or message.get("reasoning")
            or ""
        )
        return self._parse_json_response(raw_content, schema_cls)

    @staticmethod
    def _parse_json_response(raw_text: str, schema_cls: Type[T]) -> T:
        cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

        fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        first_brace = cleaned.find("{")
        first_bracket = cleaned.find("[")

        if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
            last_bracket = cleaned.rfind("]")
            if last_bracket != -1:
                arr_str = cleaned[first_bracket : last_bracket + 1]
                parsed_arr = json.loads(arr_str)
                if schema_cls is BatchEvaluationResult and isinstance(parsed_arr, list):
                    return schema_cls.model_validate({"evaluations": parsed_arr})

        if first_brace != -1:
            last_brace = cleaned.rfind("}")
            if last_brace != -1:
                cleaned = cleaned[first_brace : last_brace + 1]

        parsed_obj = json.loads(cleaned)
        return schema_cls.model_validate(parsed_obj)

    def build_search_plan(
        self,
        user_requirement: str,
        search_mode: str = "app",
        preferred_language: Optional[str] = None,
    ) -> SearchPlan:
        """Step 1: Analyze natural language requirement and generate optimal GitHub search queries."""
        if self.provider_key == "smart_zerokey" and self.model_name.startswith("local-smart-nlp"):
            return SmartZeroKeyEngine.build_plan(
                user_requirement=user_requirement,
                search_mode=search_mode,
                preferred_language=preferred_language,
                output_lang=self.output_lang,
            )

        is_en = self.output_lang == "en"
        lang_name = "English" if is_en else "Vietnamese"
        lang_hint = (
            f"\nPreferred programming language: {preferred_language}."
            if preferred_language and preferred_language not in ("All", "Tất cả")
            else ""
        )

        if search_mode == "skill":
            system_instruction = (
                "You are an expert on AI Agents (Antigravity, Claude Code, Cursor, Cline, Codex, MCP). "
                "Analyze the user's request for AI Agent Skills (SKILL.md / MCP Server / Agent Tools) on GitHub "
                "and generate 3-4 short English search queries (`github_queries`) plus 2-4 single-word English `skill_keywords`. "
                f"Write `intent_summary` and `extracted_features` in {lang_name}."
            )
            example_plan = {
                "intent_summary": "Find browser automation and Playwright testing skills for AI Agents" if is_en else "Tìm kỹ năng tự động hóa trình duyệt với Playwright cho AI Agent",
                "extracted_features": ["Browser automation", "UI testing with Playwright", "Screenshot capture"] if is_en else ["Tự động hóa trình duyệt", "Kiểm thử UI", "Chụp ảnh màn hình"],
                "target_language": None,
                "github_queries": [
                    "playwright browser agent skill",
                    "browser automation claude skill",
                    "playwright mcp server",
                ],
                "skill_keywords": ["playwright", "browser", "screenshot"],
            }
        else:
            system_instruction = (
                "You are an expert at finding open-source applications on GitHub. "
                "Analyze the user's requirement and generate 2-3 short English search queries (`github_queries`, 2-4 keywords each) "
                f"for the GitHub Search Repositories API. Write `intent_summary` and `extracted_features` in {lang_name}."
            )
            example_plan = {
                "intent_summary": "Find cross-platform personal expense tracker apps built with Flutter" if is_en else "Tìm ứng dụng quản lý chi tiêu cá nhân đa nền tảng bằng Flutter",
                "extracted_features": ["Expense tracking", "Flutter cross-platform", "Offline storage"] if is_en else ["Quản lý thu chi", "Đa nền tảng Flutter", "Hỗ trợ lưu trữ offline"],
                "target_language": "Dart",
                "github_queries": [
                    "expense tracker flutter",
                    "personal finance app flutter",
                    "budget tracker offline flutter",
                ],
                "skill_keywords": [],
            }

        prompt = (
            f"User requirement: \"{user_requirement}\"{lang_hint}\n"
            f"Output language for summaries/features: {lang_name}.\n"
            "Return ONLY valid JSON matching the example structure."
        )

        try:
            plan = self._call_llm_json(
                system_instruction=system_instruction,
                user_prompt=prompt,
                schema_cls=SearchPlan,
                example_json=example_plan,
            )
            if not plan.github_queries:
                raise ValueError("Empty github_queries from LLM")
        except Exception:
            if self.provider_key == "smart_zerokey":
                return SmartZeroKeyEngine.build_plan(
                    user_requirement=user_requirement,
                    search_mode=search_mode,
                    preferred_language=preferred_language,
                    output_lang=self.output_lang,
                )
            raise

        if preferred_language and preferred_language not in ("All", "Tất cả"):
            plan.target_language = preferred_language
            updated_queries = []
            for q in plan.github_queries:
                if "language:" not in q.lower():
                    updated_queries.append(f"{q} language:{preferred_language}")
                else:
                    updated_queries.append(q)
            plan.github_queries = updated_queries

        return plan

    def evaluate_candidates(
        self,
        user_requirement: str,
        search_plan: SearchPlan,
        candidates: List[RepoCandidate],
        search_mode: str = "app",
    ) -> List[RepoEvaluation]:
        """Step 2: Read README and SKILL.md excerpts, summarize, and score match (0-100)."""
        if not candidates:
            return []

        if self.provider_key == "smart_zerokey" and self.model_name.startswith("local-smart-nlp"):
            return SmartZeroKeyEngine.evaluate_candidates(
                user_requirement=user_requirement,
                search_plan=search_plan,
                candidates=candidates,
                search_mode=search_mode,
                output_lang=self.output_lang,
            )

        baseline_evals = SmartZeroKeyEngine.evaluate_candidates(
            user_requirement=user_requirement,
            search_plan=search_plan,
            candidates=candidates,
            search_mode=search_mode,
            output_lang=self.output_lang,
        )
        baseline_map: Dict[str, RepoEvaluation] = {
            ev.full_name.lower(): ev for ev in baseline_evals
        }

        is_en = self.output_lang == "en"
        lang_name = "English" if is_en else "Vietnamese"

        if search_mode == "skill":
            system_instruction = (
                "You are an AI Agent Skill & MCP Evaluator. "
                "Analyze the metadata and SKILL.md / README.md excerpts of each candidate repository, "
                "assign a `match_score` (0-100), classify `category_badge`, list `compatible_agents`, "
                f"and write `summary_vi`, `key_features`, `matching_reasons`, and `missing_or_caveats` in {lang_name}."
            )
        else:
            system_instruction = (
                "You are an Open-Source Application Evaluator on GitHub. "
                "Analyze the metadata and README.md excerpt of each candidate repository, "
                "assign a `match_score` (0-100), determine `is_actual_app` (True/False), "
                f"and write `summary_vi`, `key_features`, `matching_reasons`, and `missing_or_caveats` in {lang_name}."
            )

        excerpt_limit = 900 if self.provider_key == "smart_zerokey" else 1800

        repos_context_blocks = []
        for idx, c in enumerate(candidates, start=1):
            topics_str = ", ".join(c.topics[:8]) if c.topics else "None"
            skill_info_block = ""
            if search_mode == "skill":
                paths_str = (
                    ", ".join(c.skill_paths[:6])
                    if c.skill_paths
                    else "No standalone SKILL.md (see README)"
                )
                skill_info_block = f"- Discovered SKILL.md files: {paths_str}\n"
                if c.skill_md_excerpt:
                    skill_info_block += f"- SKILL.md Excerpt:\n{c.skill_md_excerpt[:excerpt_limit]}\n"

            block = (
                f"=== REPO #{idx}: {c.full_name} ===\n"
                f"- Description: {c.description}\n"
                f"- Language: {c.language} | Stars: {c.stars} | Updated: {c.updated_at} | Topics: {topics_str}\n"
                f"{skill_info_block}"
                f"- README Excerpt:\n{c.readme_excerpt[:excerpt_limit]}\n"
            )
            repos_context_blocks.append(block)

        joined_repos = "\n".join(repos_context_blocks)
        example_eval = {
            "evaluations": [
                {
                    "full_name": candidates[0].full_name,
                    "match_score": 88,
                    "is_actual_app": True,
                    "category_badge": (
                        ("🧩 Standard SKILL.md" if is_en else "🧩 SKILL.md Chuẩn")
                        if search_mode == "skill"
                        else ("📦 Complete App" if is_en else "📦 Ứng dụng hoàn chỉnh")
                    ),
                    "compatible_agents": ["Antigravity", "Claude Code", "Cursor"] if search_mode == "skill" else [],
                    "summary_vi": "Concise summary of core functionality." if is_en else "Tóm tắt ngắn gọn chức năng chính.",
                    "key_features": ["Key feature 1", "Key feature 2"],
                    "matching_reasons": ["Why it matches user requirements"],
                    "missing_or_caveats": ["Limitations or caveats to note"],
                    "quick_start": f"git clone {candidates[0].html_url}.git",
                }
            ]
        }

        prompt = (
            f"USER REQUIREMENT: \"{user_requirement}\"\n"
            f"OUTPUT LANGUAGE: {lang_name}\n\n"
            f"CANDIDATE REPOSITORIES ({len(candidates)}):\n{joined_repos}\n\n"
            "Return JSON with an `evaluations` array evaluating all candidate repositories above."
        )

        try:
            batch_result = self._call_llm_json(
                system_instruction=system_instruction,
                user_prompt=prompt,
                schema_cls=BatchEvaluationResult,
                example_json=example_eval,
            )
        except Exception:
            if self.provider_key == "smart_zerokey":
                return baseline_evals
            raise

        eval_map: Dict[str, RepoEvaluation] = {
            ev.full_name.lower(): ev for ev in batch_result.evaluations if ev.full_name
        }

        final_evaluations: List[RepoEvaluation] = []
        for c in candidates:
            ev = eval_map.get(c.full_name.lower())
            base_ev = baseline_map[c.full_name.lower()]
            if ev is not None:
                ev.full_name = c.full_name
                if not ev.summary_vi:
                    ev.summary_vi = base_ev.summary_vi
                if not ev.key_features:
                    ev.key_features = base_ev.key_features
                if not ev.matching_reasons:
                    ev.matching_reasons = base_ev.matching_reasons
                if not ev.missing_or_caveats:
                    ev.missing_or_caveats = base_ev.missing_or_caveats
                if not ev.quick_start:
                    ev.quick_start = base_ev.quick_start
                if search_mode == "skill" and not ev.compatible_agents:
                    ev.compatible_agents = base_ev.compatible_agents
                final_evaluations.append(ev)
            else:
                final_evaluations.append(base_ev)

        return final_evaluations
