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


def get_date_from_filename(filename):
    date_str = filename.split('.')[0]
    return datetime.strptime(date_str, '%Y%m%d')


def organize_articles(articles):
    return [{a['title']: a['path'].replace('docs/', '')} for a in articles]


def organize_archive_by_year(articles):
    archive_nav = defaultdict(list)
    for article in articles:
        year = article['date'].year
        archive_nav[year].append({article['title']: article['path'].replace('docs/', '')})
    return [{str(year): items} for year, items in sorted(archive_nav.items(), reverse=True)]


def update_mkdocs_yml():
    base_path = 'docs/zh'
    folders = ['archive', 'articles', 'festivals', 'workshops', 'about']
    folder_nav_mapping = {
        'festivals': '艺术节',
        'workshops': '工作坊',
        'articles': '精选文章',
        'archive': '活动存档',
        'about': '关于'
    }

    all_articles = []
    nav_translations = {}

    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        for file in os.listdir(folder_path):
            if file.endswith('.md'):
                file_path = os.path.join(folder_path, file)
                title, en_title = get_article_info(file_path)
                date = get_date_from_filename(file)
                all_articles.append({
                    'path': file_path,
                    'title': title,
                    'en_title': en_title,
                    'date': date,
                    'folder': folder
                })
                nav_translations[title] = en_title

    # 按日期排序所有文章
    all_articles.sort(key=lambda x: x['date'], reverse=True)

    # 更新 mkdocs.yml
    with open('mkdocs.yml', 'r', encoding='utf-8') as file:
        mkdocs_config = yaml.safe_load(file)

    # 更新 nav_translations
    mkdocs_config['plugins'][1]['i18n']['languages'][1]['nav_translations'].update(nav_translations)

    # 更新 nav，保持顶层顺序不变
    nav = mkdocs_config['nav']

    # 更新 festivals 和 workshops
    for item in nav:
        if isinstance(item, dict):
            nav_key = list(item.keys())[0]
            if nav_key in folder_nav_mapping.values():
                folder = next(k for k, v in folder_nav_mapping.items() if v == nav_key)
                folder_articles = [a for a in all_articles if a['folder'] == folder]
                if nav_key == '活动存档':
                    item[nav_key] = organize_archive_by_year(folder_articles)
                else:
                    item[nav_key] = organize_articles(folder_articles)

    # 写回 mkdocs.yml
    with open('mkdocs.yml', 'w', encoding='utf-8') as file:
        yaml.dump(mkdocs_config, file, allow_unicode=True)


if __name__ == '__main__':
    update_mkdocs_yml()
