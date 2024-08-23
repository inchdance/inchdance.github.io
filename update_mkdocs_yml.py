import os
import yaml
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict


def get_article_info(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    soup = BeautifulSoup(content, 'html.parser')
    title = soup.title.string.strip() if soup.title else os.path.basename(file_path)

    # 获取英文标题
    en_file_path = file_path.replace('/zh/', '/en/')
    if os.path.exists(en_file_path):
        with open(en_file_path, 'r', encoding='utf-8') as en_file:
            en_content = en_file.read()
        en_soup = BeautifulSoup(en_content, 'html.parser')
        en_title = en_soup.title.string.strip() if en_soup.title else title
    else:
        en_title = title
    return title, en_title


def organize_articles_by_folder(folder_path, articles):
    folder_structure = {}
    for article in articles:
        relative_path = os.path.relpath(article['path'], folder_path)
        parts = relative_path.split(os.sep)
        current = folder_structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[article['title']] = f"zh/{article['folder']}/{relative_path}"
    return folder_structure


def dict_to_list(d, current_path=''):
    result = []
    for key, value in d.items():
        if isinstance(value, dict):
            result.append({key: dict_to_list(value, key)})
        else:
            result.append({key: value})
    return result


def update_mkdocs_yml():
    base_path = 'docs/zh'
    folder_en = ['archive', 'articles', 'festivals', 'workshops', 'about', 'performance']
    folder_cn = ['活动存档', '精选文章', '艺术节', '工作坊', '关于', '演出']

    all_articles = []
    nav_translations = {}

    for folder in folder_en:
        folder_path = os.path.join(base_path, folder)
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    title, en_title = get_article_info(file_path)
                    date = file.split(".")
                    all_articles.append({
                        'path': file_path,
                        'title': title,
                        'en_title': en_title,
                        'date': date,
                        'folder': folder
                    })

    # 按日期排序所有文章
    all_articles.sort(key=lambda x: x['date'], reverse=True)

    # 更新 mkdocs.yml
    with open('mkdocs.yml', 'r', encoding='utf-8') as file:
        mkdocs_config = yaml.safe_load(file)

    # 更新 nav，保持顶层顺序不变
    nav = mkdocs_config['nav']

    # 更新 festivals、workshops 和 archive
    for item in nav:
        if isinstance(item, dict):
            nav_key = list(item.keys())[0]
            if nav_key in folder_cn:
                folder = folder_en[folder_cn.index(nav_key)]
                folder_path = os.path.join(base_path, folder)
                folder_articles = [a for a in all_articles if a['folder'] == folder]
                folder_structure = organize_articles_by_folder(folder_path, folder_articles)
                new_items = dict_to_list(folder_structure)

                item[nav_key] = new_items

                # 更新翻译
                for article in folder_articles:
                    nav_translations[article['title']] = article['en_title']

    # 更新 nav_translations
    mkdocs_config['plugins'][1]['i18n']['languages'][1]['nav_translations'].update(nav_translations)

    # 写回 mkdocs.yml
    with open('mkdocs.yml', 'w', encoding='utf-8') as file:
        yaml.dump(mkdocs_config, file, allow_unicode=True)


if __name__ == '__main__':
    update_mkdocs_yml()
