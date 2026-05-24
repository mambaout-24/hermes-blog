#!/usr/bin/env python3
"""
Hermes Blog Auto-Publisher
多Agent协作：选题 → 创作 → 发布
使用 Jekyll + Chirpy 主题，写入 _posts/ 目录
"""

import os
import json
import subprocess
import sys
import tempfile
from datetime import datetime

REPO_DIR = "/opt/data/hermes-blog"
POSTS_DIR = os.path.join(REPO_DIR, "_posts")

def run(cmd, cwd=None, env=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd or REPO_DIR, env=env)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def git_push():
    """GitHub 发布"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return False, "GITHUB_TOKEN 环境变量未设置", ""

    run("git add -A")
    stdout, stderr, code = run(f"git commit -m \"auto publish {datetime.now().strftime('%Y-%m-%d %H:%M')}\"")
    if "nothing to commit" in stdout.lower() or "nothing to commit" in stderr.lower():
        return True, "无新内容，跳过推送", ""

    askpass = """#!/bin/sh
case "$1" in
  *Username*) printf '%s\n' 'mambaout-24' ;;
  *Password*) printf '%s\n' "$GITHUB_TOKEN" ;;
  *) printf '%s\n' '' ;;
esac
"""
    with tempfile.NamedTemporaryFile("w", delete=False) as helper:
        helper.write(askpass)
        helper_path = helper.name
    try:
        os.chmod(helper_path, 0o700)
        env = os.environ.copy()
        env["GIT_ASKPASS"] = helper_path
        env["GIT_TERMINAL_PROMPT"] = "0"
        stdout, stderr, code = run("git push origin main", env=env)
        return code == 0, stdout, stderr
    finally:
        os.unlink(helper_path)

def publish_article(title, content, categories=None, tags=None):
    """保存文章到 _posts/ 目录并推送"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = title.lower().replace(' ', '-')
    safe_title = "".join(c for c in safe_title if c.isalnum() or c in '-_')
    filename = f"{date_str}-{safe_title[:50]}.md"

    cats = categories or ["AI"]
    tg = tags or ["自动化"]

    frontmatter = f"""---
title: {title}
date: {date_str} 08:00:00 +0800
categories: {json.dumps(cats, ensure_ascii=False)}
tags: {json.dumps(tg, ensure_ascii=False)}
---

"""
    full_content = frontmatter + content

    os.makedirs(POSTS_DIR, exist_ok=True)
    filepath = os.path.join(POSTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)

    success, stdout, stderr = git_push()
    return success, filepath, stdout, stderr

if __name__ == "__main__":
    input_data = sys.stdin.read()
    if input_data.strip().startswith("{"):
        data = json.loads(input_data)
    else:
        data = {"content": input_data}

    title = data.get("title", f"未命名文章 {datetime.now().strftime('%Y-%m-%d')}")
    content = data.get("content", input_data)
    categories = data.get("categories", ["AI"])
    tags = data.get("tags", ["自动化"])

    ok, path, out, err = publish_article(title, content, categories, tags)
    result = {"success": ok, "path": path}
    if ok:
        basename = os.path.basename(path)
        slug = basename.replace(".md", "").split("-", 3)[-1] if "-" in basename else basename.replace(".md", "")
        result["url"] = f"https://mambaout-24.github.io/hermes-blog/posts/{slug}/"
    else:
        result["error"] = err
    print(json.dumps(result, ensure_ascii=False))
