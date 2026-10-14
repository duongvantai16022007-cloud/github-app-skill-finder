from typing import List, Optional
from pydantic import BaseModel, Field


class SearchPlan(BaseModel):
    """Search plan analyzed from the user's natural language requirement."""

    intent_summary: str = Field(
        default="Search for matching open-source applications or AI agent skills on GitHub",
        description="Concise summary of the application or AI Agent Skill the user is looking for.",
    )
    extracted_features: List[str] = Field(
        default_factory=list,
        description="List of core features, agent capabilities, or technical requirements extracted from the user prompt.",
    )
    target_language: Optional[str] = Field(
        default=None,
        description="Primary programming language if explicitly specified (e.g., Python, TypeScript, Dart, Rust, Go). Null if not required.",
    )
    github_queries: List[str] = Field(
        default_factory=list,
        description=(
            "List of 2 to 4 optimized search queries for the GitHub Search Repositories API "
            "(using technical English keywords). Do not include stars:> here."
        ),
    )
    skill_keywords: List[str] = Field(
        default_factory=list,
        description="List of 2-4 short English keywords representing the skill (used to filter SKILL.md files in Agent Skill mode).",
    )


class RepoCandidate(BaseModel):
    """Repository metadata collected from GitHub API along with README and SKILL.md excerpts."""

    full_name: str
    html_url: str
    description: str = ""
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    language: str = "Unknown"
    topics: List[str] = Field(default_factory=list)
    license_name: str = "Unknown"
    updated_at: str = ""
    homepage: str = ""
    default_branch: str = "main"
    readme_excerpt: str = ""
    skill_paths: List[str] = Field(default_factory=list)
    skill_md_excerpt: str = ""


class RepoEvaluation(BaseModel):
    """Evaluation and scoring result for a repository (App or Agent Skill) based on README / SKILL.md."""

    full_name: str = Field(
        default="",
        description="Full repository name in owner/repo format.",
    )
    match_score: int = Field(
        default=70,
        description="Match score from 0 to 100 based on how well the repository satisfies the user's requirements.",
    )
    is_actual_app: bool = Field(
        default=True,
        description=(
            "In App mode: True if it is a complete usable application. "
            "In Agent Skill mode: True if it provides an actual SKILL.md, MCP server/tool, or usable agent skill."
        ),
    )
    category_badge: str = Field(
        default="📦 Complete App",
        description=(
            "Short category badge. E.g. for App: '📦 Complete App', '🛠️ CLI Tool', '📚 Library / List'. "
            "E.g. for Skill: '🧩 Standard SKILL.md', '🗂️ Skill Pack', '🔌 MCP Server / Tool', '📜 Agent Rules / Workflow'."
        ),
    )
    compatible_agents: List[str] = Field(
        default_factory=list,
        description="List of compatible AI Agents (e.g., Antigravity, Claude Code, Cursor, Cline, Codex, LangChain, AutoGen...).",
    )
    summary_vi: str = Field(
        default="",
        description="Concise summary (2-3 sentences) of the app or agent skill based on README / SKILL.md (in the requested output language).",
    )
    key_features: List[str] = Field(
        default_factory=list,
        description="List of 3-5 notable features or capabilities extracted from README / SKILL.md (in the requested output language).",
    )
    matching_reasons: List[str] = Field(
        default_factory=list,
        description="Points in README / SKILL.md demonstrating why this repository matches the user's requirements.",
    )
    missing_or_caveats: List[str] = Field(
        default_factory=list,
        description="Missing features or caveats/limitations to note.",
    )
    quick_start: Optional[str] = Field(
        default=None,
        description="Quick installation command or command to integrate the Skill into an AI Agent (git clone, copy SKILL.md, npx, mcp config...).",
    )


class BatchEvaluationResult(BaseModel):
    """Batch evaluation results for all candidate GitHub repositories."""

    evaluations: List[RepoEvaluation] = Field(
        default_factory=list,
        description="List of evaluation objects for each candidate repository.",
    )
