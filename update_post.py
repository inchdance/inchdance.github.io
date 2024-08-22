import hashlib
import os
import re
import yaml

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from llm_html_translator import translate_html


def get_html(url):
    """获取微信公众号页面的 HTML"""
    response = requests.get(url)
    return response.text


def clean_html(html_content, article_id=None):
    """
    清理 HTML，提取标题和内容，并创建新的 HTML 结构

    :param html_content: 原始 HTML 内容
    :param article_id: 文章 ID（可选，用于日志）
    :return: 清理后的 HTML 字符串，如果处理失败则返回 None
    """
    # 检查是否存在必要的元素
    if '<div id="js_article"' not in html_content:
        print(f"警告: 文章 {article_id} 缺少内容")
        return None

    # 提取标题和内容
    title_match = re.search(r'<h1 class="rich_media_title.*?>(.*?)</h1>', html_content, re.DOTALL)
    content_match = re.search(r'<div class="rich_media_content.*?>(.*?)</div>', html_content, re.DOTALL)

    if not title_match or not content_match:
        print(f"警告: 文章 {article_id} 缺少标题或内容")
        return None

    title = title_match.group(1).strip()
    content = content_match.group(1).strip()

    # 创建新的HTML结构
    new_html = f'''
<html>
  <head>
    <meta charset="utf-8">
    <title>{title}</title>
  </head>
  <body>
    <div id="img-content" class="rich_media_wrp">
      <h1 class="rich_media_title">{title}</h1>
      <div class="rich_media_content">{content}</div>
    </div>
  </body>
</html>
'''

    return new_html


def process_and_replace_images(html):
    """获取 HTML 中的图片链接并下载到 docs/assets/images"""
    soup = BeautifulSoup(html, 'html.parser')
    for img in soup.find_all('img'):
        img_url = img.get('src') if img.get('src') else img.get('data-src')
        if not img_url or not img_url.startswith("http"):
            print(f"跳过非法图片链接：{img_url}")
            continue
        try:
            # 下载图片内容
            response = requests.get(img_url, timeout=10)
            img_content = response.content

            # 计算 MD5 哈希值
            md5_hash = hashlib.md5(img_content).hexdigest()

            # 获取原始文件扩展名
            parsed_url = urlparse(img_url)
            query_params = parse_qs(parsed_url.query)
            wx_fmt = query_params.get('wx_fmt', [''])[0]

            # 根据 wx_fmt 确定文件扩展名
            if wx_fmt:
                file_extension = f".{wx_fmt}"
            else:
                # 如果没有 wx_fmt 参数，尝试从 Content-Type 获取
                content_type = response.headers.get('Content-Type', '')
                if 'png' in content_type:
                    file_extension = '.png'
                elif 'gif' in content_type:
                    file_extension = '.gif'
                else:
                    file_extension = '.jpg'

            # 创建新的文件名
            new_filename = f"{md5_hash[:10]}{file_extension}"
            save_path = os.path.join('docs', 'assets', 'images', new_filename)
            replace_path = f'/assets/images/{new_filename}'

            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(img_content)

            # 替换 HTML 中的图片链接
            img['src'] = replace_path
            if img.has_attr('data-src'):
                img['data-src'] = replace_path
                print(f"已下载并保存图片：{img_url} -> {replace_path}")
        except Exception as e:
            print(f"下载图片时出错 {img_url}: {str(e)}")
    return str(soup)


def save_as_md(html, target_md):
    """将 HTML 存为 Markdown"""
    soup = BeautifulSoup(html, 'html.parser')
    pretty_html = soup.prettify()

    with open(target_md, 'w', encoding='utf-8') as f:
        f.write(pretty_html)


def auto_translate(src_md, target_en_md):
    """自动翻译 Markdown 文件"""
    with open(src_md, 'r', encoding='utf-8') as f:
        content = f.read()
    translated_html = translate_html(content)
    with open(target_en_md, 'w', encoding='utf-8') as f:
        f.write(translated_html)


def update_mkdocs(target_md, target_en_md):
    """更新 mkdocs.yml"""
    with open('mkdocs.yml', 'r') as f:
        config = yaml.safe_load(f)

    # 添加新的页面到 nav
    config['nav'].append({os.path.basename(target_md): target_md})
    config['nav'].append({f"{os.path.basename(target_md)} (EN)": target_en_md})

    with open('mkdocs.yml', 'w') as f:
        yaml.dump(config, f)


def main(src_post, target_md, target_en_md):
    """
    # 1. 提取微信公众号页面里的 html
    src_html = get_html(src_post)

    # 2. 清理 html
    clean_html_content = clean_html(src_html)

    # 3. 获取 html 中的图片链接，下载到本地，并替换链接
    local_html = process_and_replace_images(clean_html_content)

    # 4. 将 html 存为 markdown
    save_as_md(local_html, target_md)

    # 5. 自动翻译
    auto_translate(target_md, target_en_md)
    """

    # 7. 更新 mkdocs.yml
    update_mkdocs(target_md, target_en_md)

    print("处理完成！")


if __name__ == "__main__":
    SRC_POST = "https://mp.weixin.qq.com/s/PGgpRFPvDemTlGAC_BVebw"  # 来源微信公众号文章链接
    NAV_MAP = ("寻找2017年的你", "find_2017_you", "find_2017_you")
    TARGET_MD = f"docs/zh/festivals/20240821.{NAV_MAP[2]}.md"  # 目标 markdown 文件路径
    TARGET_EN_MD = f"docs/en/festivals/20240821.{NAV_MAP[2]}.md"  # 目标英文 markdown 文件路径
    main(SRC_POST, TARGET_MD, TARGET_EN_MD)
