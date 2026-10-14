import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
import requests

from models import RepoCandidate


class GitHubClient:
    """Client giao tiếp với GitHub Search API, hỗ trợ tìm App và tìm Agent Skills (SKILL.md / MCP)."""

    BASE_API_URL = "https://api.github.com"
    RAW_BASE_URL = "https://raw.githubusercontent.com"

    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token.strip() if github_token else None
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "GitHub-App-And-Skill-Finder-AI/2.0",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        self.session.headers.update(headers)

    def _item_to_candidate(self, item: dict) -> Optional[RepoCandidate]:
        full_name = item.get("full_name")
        if not full_name:
            return None
        license_info = item.get("license") or {}
        license_name = (
            license_info.get("spdx_id")
            or license_info.get("name")
            or "Unknown"
        )
        return RepoCandidate(
            full_name=full_name,
            html_url=item.get("html_url", f"https://github.com/{full_name}"),
            description=item.get("description") or "",
            stars=item.get("stargazers_count", 0),
            forks=item.get("forks_count", 0),
            open_issues=item.get("open_issues_count", 0),
            language=item.get("language") or "Unknown",
            topics=item.get("topics") or [],
            license_name=license_name,
            updated_at=(item.get("pushed_at") or item.get("updated_at") or "")[:10],
            homepage=item.get("homepage") or "",
            default_branch=item.get("default_branch") or "main",
        )

    def _run_single_search(self, query_str: str, per_page: int = 10) -> List[dict]:
        try:
            resp = self.session.get(
                f"{self.BASE_API_URL}/search/repositories",
                params={
                    "q": query_str,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(per_page, 30),
                },
                timeout=12,
            )
            if resp.status_code == 200:
                return resp.json().get("items", [])
        except requests.RequestException:
            pass
        return []

    def search_repositories(
        self,
        queries: List[str],
        min_stars: int = 10,
        per_query_limit: int = 8,
        max_candidates: int = 10,
        search_mode: str = "app",
        skill_keywords: Optional[List[str]] = None,
    ) -> List[RepoCandidate]:
        """Thực thi danh sách câu lệnh tìm kiếm trên GitHub (hỗ trợ cả chế độ App và Agent Skill)."""
        candidates_by_name: Dict[str, RepoCandidate] = {}

        for raw_query in queries:
            q = raw_query.strip()
            if not q:
                continue
            if min_stars > 0 and "stars:" not in q:
                q_with_stars = f"{q} stars:>={min_stars}"
            else:
                q_with_stars = q

            items = self._run_single_search(q_with_stars, per_page=per_query_limit)
            # Nếu query kết hợp quá chặt trả về 0 kết quả, tự động nới lỏng
            if not items and min_stars > 0:
                items = self._run_single_search(q, per_page=per_query_limit)

            for item in items:
                candidate = self._item_to_candidate(item)
                if candidate and candidate.full_name not in candidates_by_name:
                    candidates_by_name[candidate.full_name] = candidate
                if len(candidates_by_name) >= max_candidates * 2:
                    break

            # Nếu không có GitHub Token và đã gom đủ ứng viên, dừng sớm để tiết kiệm Rate Limit (10 req/phút)
            if not self.github_token and len(candidates_by_name) >= max_candidates:
                break

        # Nếu vẫn chưa có kết quả nào, thử fallback bằng 2 từ khóa đầu tiên
        if not candidates_by_name and queries:
            words = [w for w in queries[0].split() if not w.startswith(("language:", "stars:"))]
            if len(words) >= 2:
                fallback_q = " ".join(words[:2])
                for item in self._run_single_search(fallback_q, per_page=max_candidates):
                    candidate = self._item_to_candidate(item)
                    if candidate and candidate.full_name not in candidates_by_name:
                        candidates_by_name[candidate.full_name] = candidate

        # Nếu ở chế độ tìm Agent Skill và có GitHub Token, tìm thêm qua Code Search cho filename:SKILL.md
        if search_mode == "skill" and self.github_token and skill_keywords:
            kw_str = " ".join(skill_keywords[:2]).strip()
            if kw_str:
                try:
                    code_resp = self.session.get(
                        f"{self.BASE_API_URL}/search/code",
                        params={
                            "q": f"{kw_str} filename:SKILL.md",
                            "per_page": 8,
                        },
                        timeout=10,
                    )
                    if code_resp.status_code == 200:
                        for code_item in code_resp.json().get("items", []):
                            repo_info = code_item.get("repository") or {}
                            full_name = repo_info.get("full_name")
                            path = code_item.get("path", "")
                            if not full_name:
                                continue
                            if full_name in candidates_by_name:
                                if path and path not in candidates_by_name[full_name].skill_paths:
                                    candidates_by_name[full_name].skill_paths.append(path)
                            elif len(candidates_by_name) < max_candidates * 2:
                                r_detail = self.session.get(
                                    f"{self.BASE_API_URL}/repos/{full_name}", timeout=8
                                )
                                if r_detail.status_code == 200:
                                    cand = self._item_to_candidate(r_detail.json())
                                    if cand and cand.stars >= min_stars:
                                        if path:
                                            cand.skill_paths.append(path)
                                        candidates_by_name[full_name] = cand
                except requests.RequestException:
                    pass

        all_candidates = list(candidates_by_name.values())
        selected = all_candidates[:max_candidates]

        self.populate_docs(
            selected,
            search_mode=search_mode,
            skill_keywords=skill_keywords or [],
        )
        return selected

    def _fetch_single_readme(self, candidate: RepoCandidate, max_chars: int = 4000) -> str:
        """Tải README ưu tiên qua raw.githubusercontent.com để không tốn API Rate Limit."""
        raw_filenames = ["README.md", "readme.md", "Readme.md", "README.rst", "README.txt"]
        for fname in raw_filenames:
            raw_url = f"{self.RAW_BASE_URL}/{candidate.full_name}/{candidate.default_branch}/{fname}"
            try:
                r = requests.get(raw_url, timeout=8)
                if r.status_code == 200 and r.text.strip():
                    return self._clean_markdown(r.text, max_chars=max_chars)
            except requests.RequestException:
                pass

        try:
            headers = dict(self.session.headers)
            headers["Accept"] = "application/vnd.github.raw+json"
            r = requests.get(
                f"{self.BASE_API_URL}/repos/{candidate.full_name}/readme",
                headers=headers,
                timeout=8,
            )
            if r.status_code == 200 and r.text.strip():
                return self._clean_markdown(r.text, max_chars=max_chars)
        except requests.RequestException:
            pass

        return candidate.description or "Không tìm thấy nội dung README."

    def _discover_and_fetch_skill_md(
        self,
        candidate: RepoCandidate,
        skill_keywords: List[str],
        use_tree_api: bool = True,
        max_chars: int = 3500,
    ) -> None:
        """Tìm file SKILL.md ở thư mục gốc hoặc trong cây thư mục của repository (chế độ Agent Skill)."""
        # 1. Thử tải trực tiếp các file định nghĩa kỹ năng/agent ở root qua raw.githubusercontent.com (không tốn quota API)
        for root_skill in ["SKILL.md", "skill.md", "AGENTS.md", "CLAUDE.md", ".cursorrules"]:
            raw_url = f"{self.RAW_BASE_URL}/{candidate.full_name}/{candidate.default_branch}/{root_skill}"
            try:
                r = requests.get(raw_url, timeout=6)
                if r.status_code == 200 and r.text.strip():
                    if root_skill not in candidate.skill_paths:
                        candidate.skill_paths.insert(0, root_skill)
                    if not candidate.skill_md_excerpt:
                        candidate.skill_md_excerpt = self._clean_markdown(r.text, max_chars=max_chars)
                    break
            except requests.RequestException:
                pass

        # 2. Quét cây thư mục qua Git Trees API để tìm các file SKILL.md nằm trong thư mục con (ví dụ skills/*/SKILL.md)
        if not use_tree_api:
            return

        try:
            tree_url = f"{self.BASE_API_URL}/repos/{candidate.full_name}/git/trees/{candidate.default_branch}?recursive=1"
            resp = self.session.get(tree_url, timeout=7)
            if resp.status_code == 200:
                tree_items = resp.json().get("tree", [])
                found_paths: List[str] = []
                for node in tree_items:
                    path = node.get("path", "")
                    if path.endswith(("SKILL.md", "skill.md", ".cursorrules", "AGENTS.md")):
                        found_paths.append(path)

                if found_paths:
                    kws_lower = [k.lower() for k in skill_keywords if k]
                    found_paths.sort(
                        key=lambda p: sum(1 for kw in kws_lower if kw in p.lower()),
                        reverse=True,
                    )
                    for fp in found_paths[:15]:
                        if fp not in candidate.skill_paths:
                            candidate.skill_paths.append(fp)

                    if not candidate.skill_md_excerpt and candidate.skill_paths:
                        best_path = candidate.skill_paths[0]
                        raw_url = f"{self.RAW_BASE_URL}/{candidate.full_name}/{candidate.default_branch}/{best_path}"
                        r_skill = requests.get(raw_url, timeout=6)
                        if r_skill.status_code == 200 and r_skill.text.strip():
                            candidate.skill_md_excerpt = self._clean_markdown(
                                r_skill.text, max_chars=max_chars
                            )
        except requests.RequestException:
            pass

    @staticmethod
    def _clean_markdown(text: str, max_chars: int = 4000) -> str:
        """Làm sạch bớt các thẻ HTML trang trí/badge dư thừa và cắt gọn theo ngưỡng ký tự."""
        cleaned = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        cleaned = re.sub(r"!\[[^\]]*\]\(https?://[^)]*shields\.io[^)]*\)", "", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "\n...[Đã lược bớt phần cuối]..."
        return cleaned

    def _populate_single_candidate(
        self,
        idx: int,
        candidate: RepoCandidate,
        search_mode: str,
        skill_keywords: List[str],
    ) -> None:
        candidate.readme_excerpt = self._fetch_single_readme(candidate)
        if search_mode == "skill":
            # Chỉ gọi Tree API cho tối đa 5 ứng viên đầu nếu không có GitHub Token để bảo vệ Rate Limit
            allow_tree = bool(self.github_token) or (idx < 5)
            self._discover_and_fetch_skill_md(
                candidate, skill_keywords, use_tree_api=allow_tree
            )

    def populate_docs(
        self,
        candidates: List[RepoCandidate],
        search_mode: str = "app",
        skill_keywords: Optional[List[str]] = None,
    ) -> None:
        """Tải đồng thời README (và SKILL.md nếu ở chế độ skill) cho danh sách ứng viên."""
        if not candidates:
            return
        kws = skill_keywords or []
        with ThreadPoolExecutor(max_workers=min(8, len(candidates))) as executor:
            futures = [
                executor.submit(self._populate_single_candidate, idx, c, search_mode, kws)
                for idx, c in enumerate(candidates)
            ]
            for future in futures:
                try:
                    future.result()
                except Exception:
                    pass
