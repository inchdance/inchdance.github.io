import hashlib
import os
import re

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
    soup = BeautifulSoup(html_content, 'html.parser')

    # 检查是否存在必要的元素
    article_div = soup.find('div', id='js_article')
    if not article_div:
        print(f"警告: 文章 {article_id} 缺少内容")
        return None

    # 提取标题
    title_elem = soup.find('h1', class_='rich_media_title')
    if not title_elem:
        print(f"警告: 文章 {article_id} 缺少标题")
        return None
    title = title_elem.get_text(strip=True)

    # 提取内容
    content_elem = soup.find('div', class_='rich_media_content')
    if not content_elem:
        print(f"警告: 文章 {article_id} 缺少内容")
        return None

    if 'style' in content_elem.attrs:
        styles = content_elem['style'].split(';')
        new_styles = [s for s in styles if 'visibility:' not in s and 'opacity:' not in s]
        content_elem['style'] = ';'.join(new_styles)

    content = str(content_elem)

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
      {content}
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


def main(data_block, translate_only=None):
    src_post = data_block["src_post"]
    target_md = f"docs/zh/{data_block['folder']}/{data_block['date']}.{data_block['short_tag']}.md"
    target_en_md = f"docs/en/{data_block['folder']}/{data_block['date']}.{data_block['short_tag']}.md"

    if translate_only is None:
        translate_only = False

    if not translate_only:
        # 1. 提取微信公众号页面里的 html
        src_html = get_html(src_post)
        print("获取到 HTML")

        # 2. 清理 html
        clean_html_content = clean_html(src_html)
        print("清理 HTML")

        # 3. 获取 html 中的图片链接，下载到本地，并替换链接
        local_html = process_and_replace_images(clean_html_content)
        print("完成处理图片")

        # 4. 将 html 存为 markdown
        save_as_md(local_html, target_md)
        print("保存为 Markdown")

    # 5. 自动翻译
    # auto_translate(target_md, target_en_md)
    print("自动翻译完成")


if __name__ == "__main__":
    data_json = {
        "src_post": "https://mp.weixin.qq.com/s/H5H4OG4XNenYMyrjocBIeg",
        "date": "20240809",
        "short_tag": "be_the_minority",
        "folder": "articles"
    }
    main(data_json, translate_only=False)
