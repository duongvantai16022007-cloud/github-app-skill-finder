import argparse
import importlib
import json
import os
import sys
from typing import List, Optional, Tuple

from dotenv import load_dotenv

import models
import github_client
import ai_engine

importlib.reload(models)
importlib.reload(github_client)
importlib.reload(ai_engine)

from ai_engine import FREE_AI_PROVIDERS, GitHubAIAdvisor
from github_client import GitHubClient
from models import RepoCandidate, RepoEvaluation, SearchPlan

load_dotenv()


# ==================== TERMINAL (CLI) MODE ====================
class TermColor:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"


APP_EXAMPLES_EN = [
    "Find a cross-platform personal expense tracker app built with Flutter supporting offline storage",
    "Open-source Markdown note-taking desktop app built with Electron or Tauri",
    "GUI video downloader tool for YouTube and social media on Windows/Mac",
    "Modern desktop e-book reader (EPUB/PDF) with library management and translation",
]

SKILL_EXAMPLES_EN = [
    "Find an AI Agent skill for browser automation, Playwright UI testing, and screenshot capture",
    "Skill for processing PDF, Word (DOCX), and Excel documents for Claude Code / Antigravity",
    "Collection of Agent Skills and MCP Servers for security auditing and Pull Request code review",
    "Frontend UI/UX design skill with React and Tailwind CSS for AI Coding Agents",
]

APP_EXAMPLES_VI = [
    "Tìm app quản lý chi tiêu cá nhân đa nền tảng viết bằng Flutter, hỗ trợ lưu trữ offline",
    "Ứng dụng ghi chú Markdown mã nguồn mở chạy trên Desktop (Electron hoặc Tauri)",
    "Công cụ tải video từ YouTube và mạng xã hội có giao diện đồ họa (GUI) dễ dùng cho Windows/Mac",
    "Ứng dụng đọc sách điện tử (EPUB/PDF) trên máy tính có giao diện đẹp, hỗ trợ quản lý thư viện",
]

SKILL_EXAMPLES_VI = [
    "Tìm skill giúp AI Agent tự động hóa trình duyệt web, kiểm thử UI với Playwright và chụp ảnh màn hình",
    "Skill xử lý tài liệu PDF, Word (DOCX), Excel và trích xuất dữ liệu bảng biểu cho Claude Code / Antigravity",
    "Bộ sưu tập Agent Skills và MCP Server hỗ trợ kiểm tra bảo mật code (Security Audit) và review Pull Request",
    "Skill thiết kế giao diện Frontend React / Tailwind CSS đẹp mắt và chuẩn UI/UX cho AI Coding Agent",
]


def _is_running_in_streamlit() -> bool:
    if "streamlit" not in sys.modules:
        return False
    try:
        import logging
        logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx(suppress_warning=True) is not None
    except Exception:
        return False


def run_terminal_cli() -> None:
    """Interactive & Command-Line Terminal Interface (runs via `python app.py`)."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="GitHub App & AI Agent Skill Finder (Terminal CLI)"
    )
    parser.add_argument("query", nargs="?", default=None, help="Search requirement prompt (leave empty for interactive menu)")
    parser.add_argument("-m", "--mode", choices=["app", "skill"], default="app", help="Search mode: 'app' or 'skill'")
    parser.add_argument("-p", "--provider", choices=list(FREE_AI_PROVIDERS.keys()), default="smart_zerokey", help="Free AI Provider")
    parser.add_argument("--model", default=None, help="Specific model name (e.g., glm-4-flash, glm-z1-flash)")
    parser.add_argument("-s", "--stars", type=int, default=10, help="Minimum GitHub stars (default: 10)")
    parser.add_argument("-l", "--limit", type=int, default=6, help="Max repositories to evaluate (default: 6)")
    parser.add_argument("--lang", default="All", help="Preferred programming language (e.g., Python, TypeScript, Dart)")
    parser.add_argument("--ui-lang", choices=["en", "vi"], default="en", help="Output language: 'en' (English) or 'vi' (Vietnamese)")
    parser.add_argument("-o", "--output", default=None, help="Save results to JSON file")
    args = parser.parse_args()

    def print_banner(is_en: bool = True) -> None:
        print(f"\n{TermColor.CYAN}{TermColor.BOLD}" + "=" * 78)
        if is_en:
            print(" 🚀 GITHUB APP & AI AGENT SKILL FINDER (TERMINAL EDITION)")
            print("    Search Open-Source Apps & Agent Skills (SKILL.md / MCP) in Terminal")
        else:
            print(" 🚀 MÔ HÌNH TÌM KIẾM ỨNG DỤNG & AGENT SKILL TRÊN GITHUB (TERMINAL)")
            print("    Tìm kiếm Ứng dụng & Kỹ năng AI Agent (SKILL.md / MCP) trên Terminal")
        print("=" * 78 + f"{TermColor.RESET}")

    def execute_and_display(
        q_str: str,
        mode: str,
        prov: str,
        mod_name: Optional[str],
        stars: int,
        limit: int,
        prog_lang: str,
        out_lang: str,
    ) -> Tuple[SearchPlan, List[Tuple[RepoCandidate, RepoEvaluation]]]:
        is_en = out_lang == "en"
        prov_cfg = FREE_AI_PROVIDERS.get(prov, FREE_AI_PROVIDERS["smart_zerokey"])
        chosen_model = mod_name or prov_cfg["models"][0]
        env_key = prov_cfg.get("env_key", "")
        api_key = os.getenv(env_key, "") if env_key else ""
        if prov == "glm_bigmodel" and not api_key:
            api_key = os.getenv("ZHIPUAI_API_KEY", "")

        advisor = GitHubAIAdvisor(
            provider_key=prov,
            model_name=chosen_model,
            api_key=api_key,
            output_lang=out_lang,
        )
        gh = GitHubClient(github_token=os.getenv("GITHUB_TOKEN", ""))

        print(
            f"\n{TermColor.CYAN}[1/3] 🧠 {'Analyzing requirement & generating GitHub queries' if is_en else 'Đang phân tích yêu cầu & sinh câu truy vấn GitHub'} ({chosen_model})...{TermColor.RESET}"
        )
        plan = advisor.build_search_plan(
            user_requirement=q_str,
            search_mode=mode,
            preferred_language=prog_lang,
        )

        doc_target = "README.md & SKILL.md" if mode == "skill" else "README.md"
        print(
            f"{TermColor.CYAN}[2/3] 🐙 {'Searching GitHub API & fetching' if is_en else 'Đang tìm kiếm trên GitHub & tải song song'} {doc_target}...{TermColor.RESET}"
        )
        candidates = gh.search_repositories(
            queries=plan.github_queries,
            min_stars=stars,
            per_query_limit=8,
            max_candidates=limit,
            search_mode=mode,
            skill_keywords=plan.skill_keywords,
        )

        if not candidates:
            print(f"{TermColor.RED}❌ {'No matching repositories found.' if is_en else 'Không tìm thấy repository nào thỏa mãn.'}{TermColor.RESET}")
            return plan, []

        print(
            f"{TermColor.CYAN}[3/3] 📊 {'Evaluating' if is_en else 'Đang chấm điểm'} {len(candidates)} {'repositories based on' if is_en else 'repository dựa trên'} {doc_target}...{TermColor.RESET}"
        )
        evals = advisor.evaluate_candidates(
            user_requirement=q_str,
            search_plan=plan,
            candidates=candidates,
            search_mode=mode,
        )

        eval_map = {e.full_name.lower(): e for e in evals}
        paired = [(c, eval_map[c.full_name.lower()]) for c in candidates if c.full_name.lower() in eval_map]
        paired.sort(key=lambda x: (x[1].match_score, x[0].stars), reverse=True)

        print(f"\n{TermColor.CYAN}{TermColor.BOLD}🧭 {'AI SEARCH PLAN' if is_en else 'KẾ HOẠCH TRUY VẤN AI'}:{TermColor.RESET}")
        print(f"  • {'Intent' if is_en else 'Ý định'}: {plan.intent_summary}")
        print(f"  • {'Criteria' if is_en else 'Tiêu chí'}: {', '.join(plan.extracted_features)}")
        print(f"  • GitHub Queries: {TermColor.YELLOW}{' | '.join(plan.github_queries)}{TermColor.RESET}")

        print(f"\n{TermColor.MAGENTA}{TermColor.BOLD}🏆 {'TOP RECOMMENDATIONS' if is_en else 'DANH SÁCH ĐỀ XUẤT'} ({len(paired)}):{TermColor.RESET}")
        print("-" * 78)
        for rank, (cand, ev) in enumerate(paired, start=1):
            sc_color = TermColor.GREEN if ev.match_score >= 80 else (TermColor.YELLOW if ev.match_score >= 55 else TermColor.RED)
            print(
                f"{TermColor.BOLD}#{rank}. {TermColor.CYAN}{cand.full_name}{TermColor.RESET} "
                f"[{sc_color}{TermColor.BOLD}{ev.match_score}/100{TermColor.RESET}]  {TermColor.BLUE}{ev.category_badge}{TermColor.RESET}"
            )
            print(f"   🔗 URL        : {cand.html_url}")
            print(
                f"   📊 Metadata   : ⭐ {cand.stars:,} stars | 🍴 {cand.forks:,} forks | "
                f"💻 {cand.language} | 📜 {cand.license_name} | 📅 {cand.updated_at}"
            )
            if mode == "skill" and ev.compatible_agents:
                print(f"   🤖 Agents     : {', '.join(ev.compatible_agents)}")
            if mode == "skill" and cand.skill_paths:
                print(f"   📂 SKILL.md   : {TermColor.GREEN}{', '.join(cand.skill_paths[:5])}{TermColor.RESET}")
            print(f"   📝 Summary    : {ev.summary_vi}")
            for feat in ev.key_features[:4]:
                print(f"      - {feat}")
            if ev.quick_start:
                print(f"   🚀 Quick Start: {TermColor.YELLOW}{ev.quick_start.replace(chr(10), ' | ')}{TermColor.RESET}")
            print("-" * 78)

        return plan, paired

    if args.query:
        print_banner(is_en=(args.ui_lang == "en"))
        _, paired = execute_and_display(
            q_str=args.query,
            mode=args.mode,
            prov=args.provider,
            mod_name=args.model,
            stars=args.stars,
            limit=args.limit,
            prog_lang=args.lang,
            out_lang=args.ui_lang,
        )
        if args.output and paired:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(
                    [{"rank": i, "full_name": c.full_name, "url": c.html_url, "score": e.match_score, "summary": e.summary_vi} for i, (c, e) in enumerate(paired, 1)],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"{TermColor.GREEN}✅ Saved JSON to {args.output}{TermColor.RESET}")
        return

    # Interactive Terminal Session
    print_banner(is_en=True)
    lang_in = input(f"{TermColor.YELLOW}🌐 Select Language / Chọn ngôn ngữ [1=English (Default), 2=Tiếng Việt]: {TermColor.RESET}").strip()
    out_lang = "vi" if lang_in == "2" else "en"
    is_en = out_lang == "en"

    while True:
        print(f"\n{TermColor.BOLD}{'🎯 Select Search Mode:' if is_en else '🎯 Chọn Chế độ Tìm kiếm:'}{TermColor.RESET}")
        print(f"  [1] 📱 {'Find Open-Source Apps (GitHub Apps)' if is_en else 'Tìm kiếm Ứng dụng (GitHub Apps)'}")
        print(f"  [2] 🤖 {'Find AI Agent Skills (SKILL.md / MCP / Tools)' if is_en else 'Tìm kiếm Kỹ năng AI Agent (SKILL.md / MCP)'}")
        print(f"  [q] {'Quit' if is_en else 'Thoát'}")
        m_in = input(f"{TermColor.YELLOW}👉 {'Choice [1/2/q] (Enter = 1): ' if is_en else 'Chọn [1/2/q] (Enter = 1): '}{TermColor.RESET}").strip().lower()
        if m_in in ("q", "quit", "exit"):
            break
        mode = "skill" if m_in == "2" else "app"
        examples = (SKILL_EXAMPLES_EN if mode == "skill" else APP_EXAMPLES_EN) if is_en else (SKILL_EXAMPLES_VI if mode == "skill" else APP_EXAMPLES_VI)

        print(f"\n{TermColor.BOLD}💡 {'Sample Prompts (type g1..g4):' if is_en else 'Gợi ý mẫu (nhập g1..g4):'}{TermColor.RESET}")
        for idx, ex in enumerate(examples, 1):
            print(f"  [g{idx}] {ex}")

        q_in = input(f"\n{TermColor.YELLOW}📝 {'Enter requirement (or g1..g4, q to quit): ' if is_en else 'Nhập yêu cầu (hoặc g1..g4, q để thoát): '}{TermColor.RESET}").strip()
        if not q_in:
            continue
        if q_in.lower() in ("q", "quit", "exit"):
            break
        if q_in.lower() in ("g1", "g2", "g3", "g4"):
            q_in = examples[int(q_in[1]) - 1]
            print(f"   ✔ {TermColor.CYAN}{q_in}{TermColor.RESET}")

        execute_and_display(
            q_str=q_in,
            mode=mode,
            prov="smart_zerokey",
            mod_name=None,
            stars=10,
            limit=6,
            prog_lang="All",
            out_lang=out_lang,
        )


# ==================== STREAMLIT WEB UI MODE ====================
def run_streamlit_ui() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="GitHub App & Agent Skill Finder AI",
        page_icon="🚀",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        .score-badge-high {
            background-color: #16a34a;
            color: white;
            padding: 4px 12px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
        }
        .score-badge-med {
            background-color: #ca8a04;
            color: white;
            padding: 4px 12px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
        }
        .score-badge-low {
            background-color: #dc2626;
            color: white;
            padding: 4px 12px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
        }
        .meta-pill {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 6px;
            background: rgba(128, 128, 128, 0.15);
            margin-right: 6px;
            margin-bottom: 4px;
            font-size: 0.82rem;
        }
        .agent-pill {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            background: rgba(59, 130, 246, 0.18);
            border: 1px solid rgba(59, 130, 246, 0.4);
            margin-right: 6px;
            margin-bottom: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "prompt_input" not in st.session_state:
        st.session_state.prompt_input = ""
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "search_plan" not in st.session_state:
        st.session_state.search_plan = None
    if "last_search_mode" not in st.session_state:
        st.session_state.last_search_mode = "app"

    # ==================== SIDEBAR ====================
    with st.sidebar:
        ui_lang = st.radio(
            "🌐 Language / Ngôn ngữ",
            options=["en", "vi"],
            format_func=lambda x: "🇺🇸 English" if x == "en" else "🇻🇳 Tiếng Việt",
            horizontal=True,
            index=0,
        )
        is_en = ui_lang == "en"

        st.header("🤖 Free AI Models" if is_en else "🤖 Mô hình AI Miễn phí")

        provider_keys = list(FREE_AI_PROVIDERS.keys())
        provider_labels = [
            FREE_AI_PROVIDERS[k]["label" if is_en else "label_vi"]
            for k in provider_keys
        ]

        selected_provider_idx = st.selectbox(
            "Select Free AI Provider" if is_en else "Chọn Nhà cung cấp AI (Free)",
            options=range(len(provider_keys)),
            format_func=lambda idx: provider_labels[idx],
            index=0,
        )
        provider_key = provider_keys[selected_provider_idx]
        provider_cfg = FREE_AI_PROVIDERS[provider_key]

        preset_models = provider_cfg["models"]
        custom_opt_label = "[Enter custom model ID...]" if is_en else "[Tự nhập tên model khác...]"
        selected_model = st.selectbox(
            "Select Model" if is_en else "Chọn Model",
            options=preset_models + [custom_opt_label],
            index=0,
            key=f"model_select_{provider_key}_{ui_lang}",
        )
        if selected_model == custom_opt_label:
            selected_model = st.text_input(
                "Enter Model ID" if is_en else "Nhập mã Model (Model ID)",
                value=preset_models[0],
                help="e.g., glm-4-flash, z-ai/glm-4.5-air:free, deepseek/deepseek-r1:free",
            )

        custom_base_url = None
        if provider_key in ("custom_openai", "ollama_local"):
            custom_base_url = st.text_input(
                "🌐 OpenAI-Compatible Base URL",
                value=provider_cfg["base_url"],
            )

        env_key_name = provider_cfg["env_key"]
        default_api_key = os.getenv(env_key_name, "") if env_key_name else ""
        if provider_key == "glm_bigmodel" and not default_api_key:
            default_api_key = os.getenv("ZHIPUAI_API_KEY", "")

        if provider_cfg["requires_key"]:
            help_link = provider_cfg.get("help_url", "")
            api_key_input = st.text_input(
                f"🔑 API Key ({env_key_name})",
                value=default_api_key,
                type="password",
                help=(f"Get a free key at: {help_link}" if is_en else f"Lấy key miễn phí tại: {help_link}") if help_link else None,
            )
            if help_link:
                st.caption(
                    f"🔗 [Get your free API Key here]({help_link})"
                    if is_en
                    else f"🔗 [Lấy API Key miễn phí tại đây]({help_link})"
                )
        else:
            api_key_input = ""
            st.success(
                "✅ Runs 100% free with **NO API Key required**!"
                if is_en
                else "✅ Chế độ này chạy hoàn toàn miễn phí và **không cần API Key**!"
            )

        st.divider()
        st.subheader("🐙 GitHub & Filters" if is_en else "🐙 Cấu hình GitHub & Bộ lọc")

        github_token = st.text_input(
            "GitHub Token (Optional)" if is_en else "GitHub Token (Tùy chọn)",
            value=os.getenv("GITHUB_TOKEN", ""),
            type="password",
            help=(
                "Optional. Increases GitHub search rate limits and unlocks deep SKILL.md Code Search."
                if is_en
                else "Không bắt buộc. Tăng giới hạn tìm kiếm và quét sâu file SKILL.md."
            ),
        )

        preferred_language = st.selectbox(
            "Preferred Language" if is_en else "Ngôn ngữ lập trình ưu tiên",
            options=[
                "All" if is_en else "Tất cả",
                "Python",
                "TypeScript",
                "JavaScript",
                "Dart",
                "Rust",
                "Go",
                "Java",
                "Kotlin",
                "Swift",
                "C++",
                "C#",
            ],
            index=0,
        )

        min_stars = st.number_input(
            "Minimum Stars (⭐)" if is_en else "Số lượng Stars tối thiểu (⭐)",
            min_value=0,
            max_value=50000,
            value=10,
            step=10,
        )

        max_candidates = st.slider(
            "Max Repositories to Analyze" if is_en else "Số lượng Repo tối đa để đọc & chấm điểm",
            min_value=3,
            max_value=15,
            value=8,
        )

        only_actual_items = st.checkbox(
            "Only show real Apps / Skills (hide awesome-lists)"
            if is_en
            else "Chỉ hiển thị App / Skill thực tế",
            value=False,
        )

    def format_score_badge(score: int) -> str:
        prefix = "Match" if is_en else "Độ khớp"
        if score >= 80:
            cls = "score-badge-high"
            label = f"🟢 {prefix}: {score}/100"
        elif score >= 55:
            cls = "score-badge-med"
            label = f"🟡 {prefix}: {score}/100"
        else:
            cls = "score-badge-low"
            label = f"🔴 {prefix}: {score}/100"
        return f'<span class="{cls}">{label}</span>'

    # ==================== MAIN HEADER ====================
    st.title(
        "🚀 GitHub App & AI Agent Skill Finder"
        if is_en
        else "🚀 Mô hình Tìm kiếm Ứng dụng & Agent Skills trên GitHub"
    )
    st.caption(
        "Powered by Free AI Models (**Smart Hybrid Zero-Key**, **GLM-4-Flash / GLM-Z1-Flash**, **OpenRouter Free**, **Groq**, **Ollama**) to analyze requirements, read `README.md` / `SKILL.md`, and rank repositories."
        if is_en
        else "Sử dụng các mô hình AI miễn phí (**Smart Hybrid Zero-Key**, **GLM-4-Flash / GLM-Z1-Flash**, **OpenRouter Free**, **Groq**, **Ollama**) để phân tích nhu cầu, đọc hiểu `README.md` / `SKILL.md` và xếp hạng."
    )

    mode_choice = st.radio(
        "🎯 Select Search Mode:" if is_en else "🎯 Chọn chế độ tìm kiếm:",
        options=["app", "skill"],
        format_func=lambda m: (
            ("📱 Find Open-Source Apps (GitHub Apps)" if m == "app" else "🤖 Find AI Agent Skills (SKILL.md / MCP / Agent Tools)")
            if is_en
            else ("📱 Tìm kiếm Ứng dụng / Phần mềm (GitHub Apps)" if m == "app" else "🤖 Tìm kiếm Kỹ năng cho AI Agents (SKILL.md / MCP / Agent Tools)")
        ),
        horizontal=True,
    )

    if mode_choice == "skill":
        st.info(
            "🧩 **AI Agent Skill Mode:** Automatically discovers repositories containing **`SKILL.md`**, **Skill Packs**, **MCP Servers**, and **Agent Rules** compatible with *Antigravity, Claude Code, Cursor, Cline, Codex*... and scans repository file trees to extract `SKILL.md` files directly."
            if is_en
            else "🧩 **Chế độ Tìm Skill cho AI Agents:** Tự động tìm các repository chứa **`SKILL.md`**, **Bộ sưu tập Skills**, **MCP Servers** và **Agent Rules** tương thích với *Antigravity, Claude Code, Cursor, Cline, Codex*..."
        )
        example_prompts = SKILL_EXAMPLES_EN if is_en else SKILL_EXAMPLES_VI
        input_placeholder = (
            "e.g., Find a skill that helps an AI Agent write automated unit/e2e tests, or an MCP server for PostgreSQL / Docker..."
            if is_en
            else "Ví dụ: Tìm skill giúp Agent viết bài kiểm thử tự động, hoặc MCP server kết nối PostgreSQL / Docker..."
        )
    else:
        example_prompts = APP_EXAMPLES_EN if is_en else APP_EXAMPLES_VI
        input_placeholder = (
            "e.g., Find a self-hosted Todo/Kanban task management web app with Docker support and team collaboration..."
            if is_en
            else "Ví dụ: Tìm ứng dụng quản lý công việc (Todo/Kanban) tự host bằng Docker, có giao diện web trực quan..."
        )

    st.markdown(
        "##### 💡 Quick Example Prompts (Click to fill):"
        if is_en
        else "##### 💡 Gợi ý yêu cầu mẫu (Nhấn để điền nhanh):"
    )
    cols = st.columns(len(example_prompts))
    for i, ex in enumerate(example_prompts):
        with cols[i]:
            short_label = ex[:50] + "..." if len(ex) > 50 else ex
            if st.button(f"📌 {short_label}", key=f"ex_{mode_choice}_{ui_lang}_{i}", use_container_width=True):
                st.session_state.prompt_input = ex
                st.rerun()

    user_query = st.text_area(
        "📝 Describe the App or AI Agent Skill you want to find on GitHub:"
        if is_en
        else "📝 Nhập mô tả chi tiết về Ứng dụng hoặc Agent Skill bạn muốn tìm trên GitHub:",
        value=st.session_state.prompt_input,
        height=100,
        placeholder=input_placeholder,
    )
    st.session_state.prompt_input = user_query

    if is_en:
        btn_label = "🔍 Analyze & Find AI Agent Skills on GitHub" if mode_choice == "skill" else "🔍 Analyze & Find Apps on GitHub"
    else:
        btn_label = "🔍 Phân tích & Tìm kiếm Agent Skills trên GitHub" if mode_choice == "skill" else "🔍 Phân tích & Tìm kiếm App trên GitHub"

    search_clicked = st.button(btn_label, type="primary", use_container_width=True)

    if search_clicked:
        if not user_query.strip():
            st.warning(
                "⚠️ Please enter a description of what you are looking for."
                if is_en
                else "⚠️ Vui lòng nhập mô tả yêu cầu bạn muốn tìm kiếm."
            )
        elif provider_cfg["requires_key"] and not api_key_input.strip():
            st.error(
                f"🔑 Provider **{provider_cfg['label']}** requires an API Key. Please enter your free API Key in the left sidebar, OR switch to **⚡ Free No-API-Key Mode** to run immediately!"
                if is_en
                else f"🔑 Nhà cung cấp **{provider_cfg['label_vi']}** yêu cầu API Key. Vui lòng nhập API Key ở thanh bên trái, HOẶC chuyển sang **⚡ Miễn phí Không cần API Key**!"
            )
        else:
            try:
                advisor = GitHubAIAdvisor(
                    provider_key=provider_key,
                    model_name=selected_model,
                    api_key=api_key_input,
                    custom_base_url=custom_base_url,
                    output_lang=ui_lang,
                )
                gh_client = GitHubClient(github_token=github_token)

                status_title = (
                    f"🤖 Running intelligent search & evaluation pipeline with `{selected_model}`..."
                    if is_en
                    else f"🤖 Đang vận hành quy trình tìm kiếm với model `{selected_model}`..."
                )
                with st.status(status_title, expanded=True) as status_box:
                    st.write(
                        "1️⃣ **Step 1:** Analyzing requirement and generating optimal GitHub search queries..."
                        if is_en
                        else "1️⃣ **Bước 1:** Đang phân tích yêu cầu và sinh bộ câu lệnh truy vấn GitHub tối ưu..."
                    )
                    plan: SearchPlan = advisor.build_search_plan(
                        user_requirement=user_query,
                        search_mode=mode_choice,
                        preferred_language=preferred_language,
                    )
                    st.write(f"   - **{'Intent' if is_en else 'Mục tiêu'}:** {plan.intent_summary}")
                    st.write(f"   - **{'Extracted Criteria' if is_en else 'Tiêu chí trích xuất'}:** {', '.join(plan.extracted_features)}")
                    st.write(f"   - **GitHub Queries:** `{' | '.join(plan.github_queries)}`")
                    if mode_choice == "skill" and plan.skill_keywords:
                        st.write(f"   - **`SKILL.md` Keywords:** `{', '.join(plan.skill_keywords)}`")

                    doc_target_desc = "README.md & SKILL.md" if mode_choice == "skill" else "README.md"
                    st.write(
                        f"2️⃣ **Step 2:** Querying GitHub API & concurrently fetching {doc_target_desc}..."
                        if is_en
                        else f"2️⃣ **Bước 2:** Đang truy vấn GitHub API và tải song song nội dung {doc_target_desc}..."
                    )
                    candidates: List[RepoCandidate] = gh_client.search_repositories(
                        queries=plan.github_queries,
                        min_stars=int(min_stars),
                        per_query_limit=8,
                        max_candidates=int(max_candidates),
                        search_mode=mode_choice,
                        skill_keywords=plan.skill_keywords,
                    )

                    if not candidates:
                        status_box.update(
                            label="❌ No matching repositories found on GitHub." if is_en else "❌ Không tìm thấy repository nào khớp điều kiện lọc.",
                            state="error",
                            expanded=True,
                        )
                        st.session_state.search_results = []
                        st.session_state.search_plan = plan
                        st.session_state.last_search_mode = mode_choice
                    else:
                        if mode_choice == "skill":
                            repos_with_skill_md = sum(1 for c in candidates if c.skill_paths)
                            st.write(
                                f"   - Collected **{len(candidates)}** repositories (directly discovered `SKILL.md` in **{repos_with_skill_md}** repos)."
                                if is_en
                                else f"   - Đã thu thập **{len(candidates)}** repository (phát hiện trực tiếp file `SKILL.md` trong **{repos_with_skill_md}** repo)."
                            )
                        else:
                            st.write(
                                f"   - Collected and parsed READMEs for **{len(candidates)}** candidate repositories."
                                if is_en
                                else f"   - Đã thu thập và đọc README của **{len(candidates)}** repository ứng viên."
                            )

                        st.write(
                            f"3️⃣ **Step 3:** Analyzing {doc_target_desc} and scoring match with `{selected_model}`..."
                            if is_en
                            else f"3️⃣ **Bước 3:** Đang đọc hiểu {doc_target_desc} và chấm điểm độ khớp..."
                        )
                        evaluations: List[RepoEvaluation] = advisor.evaluate_candidates(
                            user_requirement=user_query,
                            search_plan=plan,
                            candidates=candidates,
                            search_mode=mode_choice,
                        )

                        eval_by_name = {ev.full_name.lower(): ev for ev in evaluations}
                        paired_results: List[Tuple[RepoCandidate, RepoEvaluation]] = []
                        for c in candidates:
                            ev = eval_by_name.get(c.full_name.lower())
                            if ev:
                                paired_results.append((c, ev))

                        paired_results.sort(
                            key=lambda item: (item[1].match_score, item[0].stars),
                            reverse=True,
                        )

                        st.session_state.search_plan = plan
                        st.session_state.search_results = paired_results
                        st.session_state.last_search_mode = mode_choice

                        status_box.update(
                            label=(
                                f"✅ Complete! Evaluated and ranked {len(paired_results)} results."
                                if is_en
                                else f"✅ Hoàn tất! Đã phân tích và xếp hạng {len(paired_results)} kết quả."
                            ),
                            state="complete",
                            expanded=False,
                        )

            except Exception as exc:
                st.error(f"❌ {'Error during processing' if is_en else 'Đã xảy ra lỗi'}: {exc}")

    # ==================== DISPLAY RESULTS ====================
    if st.session_state.search_plan is not None:
        plan: SearchPlan = st.session_state.search_plan
        results: List[Tuple[RepoCandidate, RepoEvaluation]] = st.session_state.search_results or []
        active_mode = st.session_state.last_search_mode

        st.divider()
        with st.container():
            st.subheader("🧭 AI Query Plan Summary" if is_en else "🧭 Tóm tắt Kế hoạch Truy vấn của AI")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f"**🎯 {'Search Intent' if is_en else 'Ý định tìm kiếm'}:** {plan.intent_summary}")
                features_badges = " ".join([f"`{feat}`" for feat in plan.extracted_features])
                st.markdown(f"**🧩 {'Extracted Criteria' if is_en else 'Tiêu chí trích xuất'}:** {features_badges}")
                if active_mode == "skill" and plan.skill_keywords:
                    kw_badges = " ".join([f"`{kw}`" for kw in plan.skill_keywords])
                    st.markdown(f"**🔑 `SKILL.md` Keywords:** {kw_badges}")
            with c2:
                st.markdown("**🔎 Executed GitHub Queries:**" if is_en else "**🔎 Các câu lệnh GitHub Query đã thực thi:**")
                for q in plan.github_queries:
                    q_display = f"{q} stars:>={min_stars}" if min_stars > 0 and "stars:" not in q else q
                    st.code(q_display, language="text")

        if not results:
            st.info(
                "No matching repositories found. Try lowering the minimum stars filter or broadening your description."
                if is_en
                else "Không tìm thấy repository nào thỏa mãn. Hãy thử giảm số lượng Stars tối thiểu hoặc mở rộng mô tả."
            )
        else:
            filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
            sort_opts = (
                ["AI Match Score (High → Low)", "GitHub Stars (High → Low)", "Recently Updated"]
                if is_en
                else ["Điểm độ khớp AI (Cao → Thấp)", "Số lượng Stars (Cao → Thấp)", "Cập nhật gần nhất"]
            )
            with filter_col1:
                sort_option = st.selectbox(
                    "Sort results by:" if is_en else "Sắp xếp kết quả theo:",
                    options=sort_opts,
                    index=0,
                )
            with filter_col2:
                min_score_filter = st.slider(
                    "Minimum Match Score:" if is_en else "Lọc theo Điểm độ khớp tối thiểu:",
                    min_value=0,
                    max_value=95,
                    value=0,
                    step=5,
                )

            filtered_results = [
                (cand, ev)
                for cand, ev in results
                if ev.match_score >= min_score_filter and (not only_actual_items or ev.is_actual_app)
            ]

            if sort_option == sort_opts[1]:
                filtered_results.sort(key=lambda x: (x[0].stars, x[1].match_score), reverse=True)
            elif sort_option == sort_opts[2]:
                filtered_results.sort(key=lambda x: (x[0].updated_at, x[1].match_score), reverse=True)
            else:
                filtered_results.sort(key=lambda x: (x[1].match_score, x[0].stars), reverse=True)

            with filter_col3:
                export_payload = [
                    {
                        "rank": idx,
                        "mode": active_mode,
                        "full_name": cand.full_name,
                        "url": cand.html_url,
                        "match_score": ev.match_score,
                        "category_badge": ev.category_badge,
                        "compatible_agents": ev.compatible_agents,
                        "skill_paths": cand.skill_paths,
                        "stars": cand.stars,
                        "language": cand.language,
                        "summary": ev.summary_vi,
                        "key_features": ev.key_features,
                        "matching_reasons": ev.matching_reasons,
                        "missing_or_caveats": ev.missing_or_caveats,
                        "quick_start": ev.quick_start,
                    }
                    for idx, (cand, ev) in enumerate(filtered_results, start=1)
                ]
                st.write("")
                st.download_button(
                    label="📥 Export JSON" if is_en else "📥 Tải JSON Kết quả",
                    data=json.dumps(export_payload, ensure_ascii=False, indent=2),
                    file_name=f"github_{active_mode}_recommendations.json",
                    mime="application/json",
                    use_container_width=True,
                )

            if is_en:
                header_title = (
                    f"### 🏆 Recommended AI Agent Skills & Tools ({len(filtered_results)}/{len(results)} repos)"
                    if active_mode == "skill"
                    else f"### 🏆 Recommended Open-Source Apps ({len(filtered_results)}/{len(results)} repos)"
                )
            else:
                header_title = (
                    f"### 🏆 Danh sách Agent Skills & Tools Đề xuất ({len(filtered_results)}/{len(results)} repo)"
                    if active_mode == "skill"
                    else f"### 🏆 Danh sách Ứng dụng Đề xuất ({len(filtered_results)}/{len(results)} repo)"
                )
            st.markdown(header_title)

            for rank, (cand, ev) in enumerate(filtered_results, start=1):
                score_html = format_score_badge(ev.match_score)
                homepage_label = "🌐 Website" if is_en else "🌐 Trang chủ"
                homepage_html = (
                    f' · <a href="{cand.homepage}" target="_blank">{homepage_label}</a>'
                    if cand.homepage and cand.homepage.startswith("http")
                    else ""
                )

                with st.container(border=True):
                    top_left, top_right = st.columns([4, 1])
                    with top_left:
                        st.markdown(
                            f"#### #{rank}. [{cand.full_name}]({cand.html_url}){homepage_html}",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<span class="meta-pill">⭐ {cand.stars:,} stars</span>'
                            f'<span class="meta-pill">🍴 {cand.forks:,} forks</span>'
                            f'<span class="meta-pill">💻 {cand.language}</span>'
                            f'<span class="meta-pill">📜 {cand.license_name}</span>'
                            f'<span class="meta-pill">📅 {"Updated" if is_en else "Cập nhật"}: {cand.updated_at}</span>'
                            f'<span class="meta-pill">{ev.category_badge}</span>',
                            unsafe_allow_html=True,
                        )
                        if active_mode == "skill" and ev.compatible_agents:
                            agents_html = "".join(
                                [f'<span class="agent-pill">🤖 {ag}</span>' for ag in ev.compatible_agents]
                            )
                            compat_lbl = "Compatible with:" if is_en else "Tương thích:"
                            st.markdown(
                                f"<div style='margin-top: 4px;'>{compat_lbl} {agents_html}</div>",
                                unsafe_allow_html=True,
                            )
                    with top_right:
                        st.markdown(
                            f"<div style='text-align:right; margin-top:8px;'>{score_html}</div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown(f"**📝 {'Summary' if is_en else 'Tóm tắt'}:** {ev.summary_vi}")

                    if active_mode == "skill" and cand.skill_paths:
                        skill_links = []
                        for sp in cand.skill_paths[:8]:
                            blob_url = f"https://github.com/{cand.full_name}/blob/{cand.default_branch}/{sp}"
                            skill_links.append(f"[`{sp}`]({blob_url})")
                        more_count = len(cand.skill_paths) - 8
                        more_txt = (
                            (f" *(+{more_count} more files)*" if is_en else f" *(+{more_count} file khác)*")
                            if more_count > 0
                            else ""
                        )
                        skill_lbl = (
                            "**📂 Discovered `SKILL.md` Files:**"
                            if is_en
                            else "**📂 Các file Skill (`SKILL.md`) phát hiện trong Repo:**"
                        )
                        st.markdown(f"{skill_lbl} {' · '.join(skill_links)}{more_txt}")

                    if cand.topics:
                        topics_md = " ".join([f"`#{t}`" for t in cand.topics[:10]])
                        st.markdown(f"**🏷️ Topics:** {topics_md}")

                    detail_col1, detail_col2 = st.columns(2)
                    with detail_col1:
                        if is_en:
                            feat_title = "**✨ Skill Capabilities & Tools:**" if active_mode == "skill" else "**✨ Key Features (from README):**"
                            reason_title = "**✅ Why It Matches Your Request:**"
                        else:
                            feat_title = "**✨ Khả năng & Công cụ của Skill:**" if active_mode == "skill" else "**✨ Tính năng nổi bật (trích từ README):**"
                            reason_title = "**✅ Lý do khớp với yêu cầu của bạn:**"

                        st.markdown(feat_title)
                        for feat in ev.key_features:
                            st.markdown(f"- {feat}")

                        st.markdown(reason_title)
                        for reason in ev.matching_reasons:
                            st.markdown(f"- {reason}")

                    with detail_col2:
                        if ev.missing_or_caveats:
                            st.markdown("**⚠️ Caveats & Notes:**" if is_en else "**⚠️ Điểm lưu ý / Hạn chế:**")
                            for caveat in ev.missing_or_caveats:
                                st.markdown(f"- {caveat}")

                        if ev.quick_start:
                            if is_en:
                                qs_title = "**🚀 Quick Skill Integration / Install:**" if active_mode == "skill" else "**🚀 Quick Start / Installation:**"
                            else:
                                qs_title = "**🚀 Lệnh tích hợp Skill vào Agent / Cài đặt nhanh:**" if active_mode == "skill" else "**🚀 Cài đặt / Chạy nhanh:**"
                            st.markdown(qs_title)
                            st.code(ev.quick_start, language="bash")

                    if active_mode == "skill" and cand.skill_md_excerpt:
                        with st.expander(
                            f"🧩 View SKILL.md excerpt of {cand.full_name}"
                            if is_en
                            else f"🧩 Xem nội dung SKILL.md của {cand.full_name}"
                        ):
                            st.code(cand.skill_md_excerpt, language="markdown")

                    with st.expander(
                        f"📄 View raw README excerpt of {cand.full_name}"
                        if is_en
                        else f"📄 Xem trích đoạn README gốc của {cand.full_name}"
                    ):
                        st.text(cand.readme_excerpt)


if _is_running_in_streamlit():
    run_streamlit_ui()
elif __name__ == "__main__":
    run_terminal_cli()
