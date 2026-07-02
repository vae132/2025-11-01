#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import json
import hashlib
import requests
from bs4 import BeautifulSoup
import datetime  # 用于解析发布时间
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode, unquote

# =================== 配置项 ===================
BASE_URL = "https://andylee.pro/wp/"
DATA_DIR = "data"       # 数据存储目录
PAGE_SIZE = 10              # 每页保存文章数，根据需要调整
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}
TARGET_USERS = ["李宗恩", "andy"]  # 针对特定评论作者做高亮处理

# =================== 基础爬虫函数 ===================

def get_article_links(page=1, retries=5):
    """
    获取指定页码的所有文章链接（按最新排序）
    """
    url = f"{BASE_URL}?paged={page}"
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            if attempt > 0:
                print(f"✅ 获取文章列表成功 (尝试第 {attempt+1} 次)")
            break
        except Exception as e:
            attempt += 1
            print(f"❌ 获取文章列表出错：{e}, 尝试第 {attempt} 次")
            if attempt == retries:
                print("❌ 获取文章列表失败，继续执行")
                return []
            time.sleep(2)
    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("h2", class_="entry-title")
    links = []
    for article in articles:
        a_tag = article.find("a")
        if a_tag and "href" in a_tag.attrs:
            links.append(a_tag["href"])
    return links

def get_article_title(article_url, old_title=None, retries=5):
    """
    获取文章标题，先查找 <h1 class="post-title">，若无则查找 <h1 class="entry-title">
    若请求或解析失败，则返回 old_title（如果提供了），否则返回 "未知标题"。
    成功后打印“✅ 请求文章标题成功”及尝试次数和获取到的标题。
    """
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(article_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            if attempt > 0:
                print(f"✅ 请求文章标题成功 (尝试第 {attempt+1} 次)")
            break
        except Exception as e:
            attempt += 1
            print(f"❌ 请求文章标题出错：{e}, 尝试第 {attempt} 次")
            if attempt == retries:
                print("❌ 请求文章标题失败，继续执行")
                return old_title if old_title is not None else "未知标题"
            time.sleep(2)
    soup = BeautifulSoup(response.text, "html.parser")
    title_tag = soup.find("h1", class_="post-title")
    if not title_tag:
        title_tag = soup.find("h1", class_="entry-title")
    result = title_tag.get_text(strip=True) if title_tag else (old_title if old_title is not None else "未知标题")
    print(f"✅ 请求文章标题成功, 标题为: {result}")
    return result

def get_article_content(article_url, old_content=None, retries=5):
    """
    获取文章正文内容，尝试解析 <div class="entry-content">
    若请求或解析失败，则返回 old_content（如果提供了），否则返回 "未知内容"。
    成功后打印“✅ 请求文章内容成功”及尝试次数。
    """
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(article_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            if attempt > 0:
                print(f"✅ 请求文章内容成功 (尝试第 {attempt+1} 次)")
            break
        except Exception as e:
            attempt += 1
            print(f"❌ 请求文章内容出错：{e}, 尝试第 {attempt} 次")
            if attempt == retries:
                print("❌ 请求文章内容失败，继续执行")
                return old_content if old_content is not None else "未知内容"
            time.sleep(2)
    soup = BeautifulSoup(response.text, "html.parser")
    content_tag = soup.find("div", class_="entry-content")
    result = content_tag.decode_contents().strip() if content_tag else (old_content if old_content is not None else "未知内容")
    print("✅ 请求文章内容成功")
    return result

def get_article_time(article_url, old_time=None, retries=5):
    """
    获取文章发布时间，尝试解析 <span class="entry-date post-date"> 内的发布时间，
    若请求或解析失败，则返回 old_time（如果提供了），否则返回 ""。
    成功后打印“✅ 请求文章发布时间成功”及尝试次数。
    """
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(article_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            if attempt > 0:
                print(f"✅ 请求文章发布时间成功 (尝试第 {attempt+1} 次)")
            break
        except Exception as e:
            attempt += 1
            print(f"❌ 请求文章发布时间出错：{e}, 尝试第 {attempt} 次")
            if attempt == retries:
                print("❌ 请求文章发布时间失败，继续执行")
                return old_time if old_time is not None else ""
            time.sleep(2)
    soup = BeautifulSoup(response.text, "html.parser")
    time_span = soup.find("span", class_="entry-date post-date")
    result = ""
    if time_span:
        abbr_tag = time_span.find("abbr", class_="published")
        if abbr_tag and abbr_tag.has_attr("title"):
            iso_time = abbr_tag["title"]
            try:
                dt = datetime.datetime.fromisoformat(iso_time)
                result = dt.strftime("%Y年%m月%d日 %H:%M")
            except Exception as e:
                print("❌ 解析发布时间错误:", e)
                result = abbr_tag.get_text(strip=True)
        else:
            result = time_span.get_text(strip=True)
    print("✅ 请求文章发布时间成功:", result)
    return result

def get_comments(article_url, selected_color="white", retries=5):
    """
    获取文章的所有评论及其回复，并返回评论数据（列表字典）。
    如果请求成功但页面中无评论（例如文章本身没有评论），返回空列表并打印相应提示；
    如果请求始终失败，则返回 None 并打印错误信息。
    """
    attempt = 0
    response = None
    while attempt < retries:
        try:
            response = requests.get(article_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            if attempt > 0:
                print(f"✅ 请求文章评论成功 (尝试第 {attempt+1} 次)")
            break
        except Exception as e:
            attempt += 1
            print(f"❌ 请求文章评论出错：{e}, 尝试第 {attempt} 次")
            if attempt == retries:
                print("❌ 请求评论失败，继续执行")
                return None
            time.sleep(2)
    soup = BeautifulSoup(response.text, "html.parser")
    comment_list = soup.find("ol", class_="commentlist")
    if comment_list:
        top_comments = comment_list.find_all("li", class_="comment", recursive=False)
    else:
        top_comments = soup.find_all("li", class_="comment", recursive=False)
    results = []
    index = 0
    for comment in top_comments:
        data, index = parse_comment(comment, article_url, selected_color=selected_color, index=index)
        if data:
            results.append(data)
    if response is not None:
        if len(results) == 0:
            print("✅ 请求文章评论成功，但文章本身没有评论")
        else:
            print(f"✅ 请求文章评论成功, 共获取 {len(results)} 条评论")
    return results

# ------------------- 以下为评论解析相关 -------------------

def generate_unique_id(article_url, index):
    """
    生成唯一的ID，结合文章URL和评论索引
    """
    return hashlib.md5(f"{article_url}-{index}".encode('utf-8')).hexdigest()

def parse_comment(comment, article_url, level=0, selected_color="white", index=0):
    """
    解析评论及其子评论，并返回数据字典和最新的索引值
    """
    author_tag = comment.find("cite", class_="fn")
    if not author_tag:
        return None, index
    comment_user = author_tag.text.strip()

    time_tag = comment.find("small")
    if time_tag:
        raw_time = time_tag.get_text(strip=True)
        match = re.search(r'(\d+)\s*(\d+)\s*月,\s*(\d{4})\s+at\s+(\d+):(\d+)\s*(上午|下午)', raw_time)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            period = match.group(6)
            if period == "下午" and hour < 12:
                hour += 12
            time_text = f"{year}年{month:02d}月{day:02d}日 {hour:02d}:{minute:02d}"
        else:
            time_text = raw_time
    else:
        time_text = ""

    comment_text_tag = comment.find("div", class_="comment_text")
    if not comment_text_tag:
        return None, index

    # 删除评论中的回复按钮标签
    for reply in comment_text_tag.find_all("div", class_="reply"):
        reply.decompose()
    comment_text = comment_text_tag.decode_contents().strip()

    highlight = (comment_user in TARGET_USERS)
    current_index = index
    comment_id = generate_unique_id(article_url, current_index)
    index = current_index + 1

    data = {
        "id": comment_id,
        "author": comment_user,
        "time": time_text,
        "content": comment_text,
        "level": level,
        "highlight": highlight,
        "children": []
    }

    children_container = comment.find("ul", class_="children")
    if children_container:
        child_comments = children_container.find_all("li", class_="comment", recursive=False)
        for child in child_comments:
            child_data, index = parse_comment(child, article_url, level + 1, selected_color, index)
            if child_data:
                data["children"].append(child_data)
    return data, index

# ------------------- 以下为数据存储与更新逻辑 -------------------

def save_to_json_file(article_data, page, order, fixed=False):
    """
    将 article_data 保存为 JSON 文件到相应目录中
    如果 fixed 为 False，则保存到 data/page{page} 目录下，文件名格式：page{page}_order{order}_{unique}.json
    如果 fixed 为 True，则保存到 data/fixed 目录下，文件名保持原文件名（若存在）或新生成
    """
    unique = generate_unique_id(article_data["article_url"], order)
    if not fixed:
        folder = os.path.join(DATA_DIR, f"page{page}")
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = os.path.join(folder, f"page{page}_order{order}_{unique}.json")
    else:
        folder = os.path.join(DATA_DIR, "fixed")
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = article_data.get("filename")
        if not filename:
            filename = os.path.join(folder, f"{unique}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(article_data, f, ensure_ascii=False, indent=2)
    return filename

def load_all_local_articles():
    """
    遍历 DATA_DIR 下所有 page 文件夹，加载所有 JSON 文件，
    返回列表，每个元素为字典，包含 article_url, title, content, article_time, comments, page, order, filename 等字段。
    列表按页码和 order 升序排序（page1_order1 为最新文章）
    """
    articles = []
    if not os.path.exists(DATA_DIR):
        return articles
    for folder in os.listdir(DATA_DIR):
        folder_path = os.path.join(DATA_DIR, folder)
        if os.path.isdir(folder_path) and folder.startswith("page"):
            m = re.search(r'page(\d+)', folder)
            if not m:
                continue
            page_num = int(m.group(1))
            for filename in os.listdir(folder_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(folder_path, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        m2 = re.search(r'order(\d+)', filename)
                        order_num = int(m2.group(1)) if m2 else 0
                        data["page"] = page_num
                        data["order"] = order_num
                        data["filename"] = filepath
                        articles.append(data)
                    except Exception as e:
                        print(f"❌ 加载文件 {filepath} 出错: {e}")
    articles.sort(key=lambda x: (x["page"], x["order"]))
    return articles

def load_fixed_articles():
    """
    遍历 DATA_DIR/fixed 目录，加载所有 JSON 文件，
    返回列表，每个元素为字典，包含 article_url, title, content, article_time, comments, filename 等字段。
    """
    articles = []
    fixed_dir = os.path.join(DATA_DIR, "fixed")
    if not os.path.exists(fixed_dir):
        return articles
    for filename in os.listdir(fixed_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(fixed_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["filename"] = filepath
                articles.append(data)
            except Exception as e:
                print(f"❌ 加载固定页面文件 {filepath} 出错: {e}")
    return articles

def reassign_and_save_articles(all_articles):
    """
    将所有文章按照顺序重新分配页码和 order，
    清空原 DATA_DIR 下的 JSON 文件后，依 PAGE_SIZE 分页写入文件。
    """
    new_articles = all_articles[:]  # 拷贝列表
    # 清空 DATA_DIR 下所有 JSON 文件（建议事先备份）
    if os.path.exists(DATA_DIR):
        for root, dirs, files in os.walk(DATA_DIR):
            for f in files:
                # 如果是 fixed 目录下的文件则跳过删除
                if f.endswith(".json") and "fixed" not in root:
                    os.remove(os.path.join(root, f))
    else:
        os.makedirs(DATA_DIR)
    for idx, article in enumerate(new_articles):
        page = idx // PAGE_SIZE + 1
        order = idx % PAGE_SIZE + 1
        article["page"] = page
        article["order"] = order
        save_to_json_file(article, page, order)
    print("✅ 重新分配并保存文章完成！")

# =================== 新文章更新相关 ===================

def get_current_website_articles(max_pages=1):
    """
    从网站前 max_pages 页中获取文章链接列表，默认只取第一页（新文章总在最前面）
    """
    links = []
    for page in range(1, max_pages + 1):
        page_links = get_article_links(page)
        if not page_links:
            break
        links.extend(page_links)
    return links

def fetch_new_articles(new_urls):
    """
    针对每个新的文章 URL，爬取标题、正文、发布时间和评论，返回文章数据列表
    """
    new_articles = []
    for url in new_urls:
        print(f"爬取新文章：{url}")
        title = get_article_title(url)
        content = get_article_content(url)
        article_time = get_article_time(url)
        comments = get_comments(url)
        article_data = {
            "article_url": url,
            "title": title,
            "content": content,
            "article_time": article_time,
            "comments": comments,  # 如果请求成功但无评论，则 comments 为 []（有效结果）
            "timestamp": time.time()
        }
        new_articles.append(article_data)
        time.sleep(2)
    return new_articles

def update_new_articles():
    """
    检查网站最新文章与本地 data/page 第一篇是否一致，
    若有新文章则新文章始终插入在最前面，原文章后移，
    且只有当 n 篇新文章全部都成功爬取到有效标题、正文、发布时间和评论
    （即标题不为 “未知标题”，内容不为 “未知内容”，发布时间不为空，且评论数据不为 None；注意：如果文章本身无评论，返回 [] 是有效结果）时，
    才将 n 篇新文章合并原有文章后重新分配页码和顺序写入文件。
    """
    print("检查网站最新文章是否有更新……")
    # 对获取最新文章链接给予最多 5 次机会
    attempt = 0
    website_links = []
    while attempt < 5:
        website_links = get_current_website_articles(max_pages=1)
        if website_links:
            print(f"✅ 成功获取网站最新文章链接 (尝试第 {attempt+1} 次)")
            break
        attempt += 1
        time.sleep(5)
    if not website_links:
        print("❌ 5 次尝试后仍无法获取网站最新文章链接")
        return

    local_articles = load_all_local_articles()
    first_local_url = local_articles[0]["article_url"] if local_articles else None
    first_local_url_key = normalize_url_for_match(first_local_url) if first_local_url else None

    new_count = 0
    for link in website_links:
        # URL 做规范化后再比较，避免尾部斜杠、#comment、追踪参数造成误判
        if normalize_url_for_match(link) == first_local_url_key:
            break
        new_count += 1

    if new_count == 0:
        print("✅ 本地数据已经是最新的，无需更新文章。")
        return
    else:
        print(f"✅ 检测到 {new_count} 篇新文章。")
        new_urls = website_links[0:new_count]

    # 对 n 篇新文章的爬取，给予最多 5 次机会，要求全部文章都爬取成功
    attempt = 0
    all_valid = False
    new_articles = []
    while attempt < 5:
        new_articles = fetch_new_articles(new_urls)
        # 仅当 get_comments 返回 None 才视为请求失败；若返回 [] 则认为文章本身无评论，是有效结果
        invalid_articles = [article for article in new_articles if article["title"] == "未知标题"
                            or article["content"] == "未知内容"
                            or not article["article_time"]
                            or article["comments"] is None]
        if not invalid_articles:
            all_valid = True
            break
        else:
            print(f"第 {attempt+1} 次尝试爬取新文章未成功，问题文章: {', '.join([article['article_url'] for article in invalid_articles])}")
            attempt += 1
            time.sleep(5)
    if not all_valid:
        print("❌ 5 次尝试后仍有文章爬取不成功，新文章不写入文件")
        return

    # 如果重新爬取后全部成功，则打印成功标志
    print("✅ 新文章全部爬取成功！")

    # 全部 n 篇新文章均爬取成功，合并新文章和旧文章，并重新分配页码后写入文件
    merged_articles = new_articles + local_articles
    reassign_and_save_articles(merged_articles)

# =================== 近期留言更新（优先按 URL 匹配，标题时间兜底） ===================

def normalize_url_for_match(url):
    """
    将文章 URL 规范化，用于本地 JSON 匹配。

    为什么要这样做：
    WordPress 的“近期评论”链接经常长这样：
        https://andylee.pro/wp/xxx/#comment-123
        https://andylee.pro/wp/xxx/?replytocom=123#respond
    但本地 JSON 里保存的 article_url 可能是：
        https://andylee.pro/wp/xxx/

    如果直接用字符串 == 比较，就会匹配失败。
    这里会：
    1. 去掉 #comment / #respond 这类 fragment；
    2. 去掉 replytocom、utm、fbclid、gclid 等无关参数；
    3. 统一大小写、URL 编码、尾部斜杠；
    4. 支持相对链接转绝对链接。
    """
    if not url:
        return ""

    url = str(url).strip()
    url = urljoin(BASE_URL, url)

    parts = urlsplit(url)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()

    # 有些地方可能带 www，有些不带，统一去掉 www.
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # 解码路径，去掉尾部斜杠；根路径不要变成空
    path = unquote(parts.path or "")
    path = re.sub(r"/+/", "/", path)
    if len(path) > 1:
        path = path.rstrip("/")

    # 保留真正能定位文章的参数，例如 p=123；去掉评论、追踪参数
    keep_params = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        lk = k.lower()
        if lk == "replytocom":
            continue
        if lk.startswith("utm_"):
            continue
        if lk in {"fbclid", "gclid", "mc_cid", "mc_eid"}:
            continue
        keep_params.append((k, v))
    query = urlencode(keep_params, doseq=True)

    # fragment 直接丢掉：#comment-123 不应该影响文章匹配
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_title_for_match(title):
    """
    标题兜底匹配用：只做轻度规范化。
    注意：真正可靠的是 URL；标题可能被管理员修改，所以标题只能做兜底。
    """
    title = str(title or "")
    try:
        title = title.normalize("NFKC")
    except Exception:
        pass
    title = re.sub(r"\s+", "", title)
    return title.strip().lower()


def find_matching_local_article(local_articles, fixed_articles, title, url, new_article_time=""):
    """
    查找近期评论对应的本地 JSON 文章。

    新逻辑：
    1. 先用规范化 URL 匹配，这是最可靠的。管理员改标题也不怕。
    2. URL 找不到，再用【标题 + 发布时间】兜底。
    3. 还找不到，再用【规范化标题 + 发布时间】兜底。
    """
    target_url_key = normalize_url_for_match(url)
    target_title_key = normalize_title_for_match(title)

    # 1）优先 URL 匹配：先找 data/page，再找 data/fixed
    for article in local_articles:
        local_url_key = normalize_url_for_match(article.get("article_url", ""))
        if local_url_key and local_url_key == target_url_key:
            return article, "常规页面", "URL匹配"

    for article in fixed_articles:
        local_url_key = normalize_url_for_match(article.get("article_url", ""))
        if local_url_key and local_url_key == target_url_key:
            return article, "固定页面", "URL匹配"

    # 2）URL 没找到，再用原来的：标题 + 发布时间
    if new_article_time:
        for article in local_articles:
            if article.get("title", "") == title and article.get("article_time", "") == new_article_time:
                return article, "常规页面", "标题+发布时间匹配"

        for article in fixed_articles:
            if article.get("title", "") == title and article.get("article_time", "") == new_article_time:
                return article, "固定页面", "标题+发布时间匹配"

    # 3）再兜底：规范化标题 + 发布时间，解决空格、全角半角差异
    if new_article_time and target_title_key:
        for article in local_articles:
            if normalize_title_for_match(article.get("title", "")) == target_title_key and article.get("article_time", "") == new_article_time:
                return article, "常规页面", "规范化标题+发布时间匹配"

        for article in fixed_articles:
            if normalize_title_for_match(article.get("title", "")) == target_title_key and article.get("article_time", "") == new_article_time:
                return article, "固定页面", "规范化标题+发布时间匹配"

    return None, "", ""

def get_recent_comment_articles_collection(retries=5):
    """
    直接爬取整个近期评论区域，提取每条评论中涉及的文章标题和链接。

    返回值从原来的 dict 改成 list：
        [
            {"title": "文章标题", "url": "文章链接"},
            ...
        ]

    为什么不用 dict：
    1. dict 用标题当 key，如果标题重复，会互相覆盖；
    2. 管理员改标题后，标题本身不可靠；
    3. 我们真正应该用 URL 去匹配本地 JSON。
    """
    url = BASE_URL  # 以首页为例
    attempt = 0
    response = None

    while attempt < retries:
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            print(f"✅ 成功获取近期评论区域 (尝试第 {attempt+1} 次)")
            break
        except Exception as e:
            attempt += 1
            print(f"❌ 获取近期评论区域出错：{e}, 尝试第 {attempt} 次")
            if attempt == retries:
                print("❌ 5 次尝试后仍无法获取近期评论区域")
                return []
            time.sleep(2)

    soup = BeautifulSoup(response.text, "html.parser")
    recent_comments = soup.find("aside", id="recent-comments-5")
    if not recent_comments:
        print("✅ 未找到近期评论区域")
        return []

    articles = []
    seen_url_keys = set()
    comment_items = recent_comments.find_all("li", class_="recentcomments")

    for li in comment_items:
        a_tags = li.find_all("a", href=True)

        # WordPress 默认近期评论通常是：作者链接 + 文章链接
        # 所以有两个或更多 a 标签时，第二个一般是文章链接。
        # 如果只有一个 a 标签，就只能取第一个。
        if len(a_tags) >= 2:
            a_tag = a_tags[1]
        elif a_tags:
            a_tag = a_tags[0]
        else:
            continue

        title = a_tag.get_text(strip=True)
        link = a_tag["href"]
        url_key = normalize_url_for_match(link)

        # 同一篇文章可能有多条近期评论，去重即可，避免重复爬取同一篇文章。
        if url_key in seen_url_keys:
            continue

        seen_url_keys.add(url_key)
        articles.append({
            "title": title,
            "url": link,
            "url_key": url_key
        })

    return articles


def update_recent_comments_by_title():
    """
    对近期留言涉及的文章进行更新。

    修改后的匹配顺序：
    1. 先用 URL 匹配本地 JSON 文件，并且 URL 会先规范化；
       这样管理员修改标题后，也能找到本地文章。
    2. URL 找不到时，再用【标题 + 发布时间】兜底。
    3. 还找不到，再用【规范化标题 + 发布时间】兜底。

    找到本地文章后，重新爬取标题、正文、发布时间和评论，
    然后写回 match_found["filename"] 对应的本地 JSON 文件。
    """
    print("开始检查近期留言更新（优先 URL 匹配，标题和发布时间兜底）……")

    recent_articles = get_recent_comment_articles_collection()
    if not recent_articles:
        print("近期留言未获取到有效的文章数据。")
        return

    local_articles = load_all_local_articles()    # data/page 下的文章
    fixed_articles = load_fixed_articles()        # data/fixed 下的文章
    updated = 0

    for item in recent_articles:
        title = item.get("title", "")
        url = item.get("url", "")
        target_url_key = normalize_url_for_match(url)

        print(f"\n🔎 正在处理近期留言文章：{title}")
        print(f"   原始链接：{url}")
        print(f"   规范链接：{target_url_key}")

        # 先获取网页上最新的发布时间，给标题时间兜底匹配使用。
        # 注意：如果 URL 已经能匹配成功，标题改了也没关系。
        new_article_time = get_article_time(url, old_time="")

        match_found, location, match_method = find_matching_local_article(
            local_articles=local_articles,
            fixed_articles=fixed_articles,
            title=title,
            url=url,
            new_article_time=new_article_time
        )

        if match_found:
            if location == "常规页面":
                print(
                    f"📌 找到本地文章：第 {match_found.get('page', '?')} 页 "
                    f"第 {match_found.get('order', '?')} 篇，匹配方式：{match_method}"
                )
            else:
                print(f"📌 找到固定页面文章，匹配方式：{match_method}")

            old_local_title = match_found.get("title", "")
            if old_local_title != title:
                print(f"   本地旧标题：{old_local_title}")
                print(f"   近期区标题：{title}")

            # 重新爬取标题
            new_title = get_article_title(url, old_title=match_found.get("title"))
            if new_title != "未知标题":
                match_found["title"] = new_title
            else:
                print(f"❌ 标题爬取失败，保留原有标题：{match_found.get('title', '')}")

            # 重新爬取正文
            new_content = get_article_content(url, old_content=match_found.get("content"))
            if new_content != "未知内容":
                match_found["content"] = new_content
            else:
                print("❌ 正文爬取失败，保留原有内容")

            # 重新爬取发布时间
            new_time = get_article_time(url, old_time=match_found.get("article_time"))
            if new_time:
                match_found["article_time"] = new_time
            else:
                print("❌ 发布时间爬取失败，保留原有发布时间")

            # 重新爬取评论
            new_comments = get_comments(url)
            if new_comments is None:
                print(f"❌ 评论爬取失败：{title}，保留原有评论")
            else:
                match_found["comments"] = new_comments
                match_found["timestamp"] = time.time()

            # 为了以后更稳，顺手保存规范化后的 URL；但不强行替换成本次带 #comment 的链接
            # 如果原 article_url 为空，则补上去。
            if not match_found.get("article_url"):
                match_found["article_url"] = target_url_key

            try:
                with open(match_found["filename"], "w", encoding="utf-8") as f:
                    json.dump(match_found, f, ensure_ascii=False, indent=2)
                print(f"✅ 更新完成：{location} - {match_found.get('title', '')}")
                print(f"   写回文件：{match_found['filename']}")
                updated += 1
            except Exception as e:
                print(f"❌ 保存更新失败（标题：{match_found.get('title', '')}）：{e}")

            time.sleep(2)
        else:
            print(f"❌ 未在本地数据中找到匹配文章：{title}")
            print(f"   已尝试 URL 匹配、标题+发布时间匹配、规范化标题+发布时间匹配")
            print(f"   近期区 URL：{url}")
            print(f"   规范化 URL：{target_url_key}")
            print(f"   网页发布时间：{new_article_time or '空'}")

    print(f"\n✅ 近期留言更新完成，共更新 {updated} 篇文章。")

# =================== 主更新流程 ===================

def main_update():
    """
    主流程：
    1. 检查网站是否有新文章，如有则更新文章并重新分配页码与顺序；
    2. 检查近期留言中涉及的文章，按文章标题和发布时间匹配更新其数据；
    3. 打印更新完成提示。
    """
    update_new_articles()
    update_recent_comments_by_title()
    print("✅ 所有更新完成！")

if __name__ == "__main__":
    main_update()
