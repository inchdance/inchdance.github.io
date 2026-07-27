# 图片侵权处理与部署记录

> 处理日期:2025-07-27
> 事件:收到图片侵权投诉,需移除侵权图及其所有副本并更新线上网站

---

## 一、事件概述

被告知项目中某张图片侵权。该图用于「Beyond Dance 不止跳舞」艺术节 2024 系列推文。

处理中发现一个关键问题:**同一张侵权图在项目里以不同文件名、不同格式存在多个副本**。仅删除其中一处无法彻底解决,需要对全库做视觉比对。

最终确认并清除的 2 个文件(实为同一张图):

| 文件 | 格式 | 说明 |
|------|------|------|
| `0f56af4996.webp` | webp | 原图(首次被告侵权的) |
| `fb78bcf79f.jpg` | jpg | 同一张图的 jpg 副本,文件名 id 完全不同 |

两者尺寸(1080×711)、宽高比、微信元数据(data-ratio / data-w)完全一致,视觉哈希距离仅 2。

---

## 二、处理时间线

### 阶段 1:首次删除(原图)
- `grep -rln "0f56af4996" docs/` 定位引用
- 删除 `docs/zh/festivals/2024/20240607.beyond_dance_Impro_festival_earlybird.md` 中引用该图的 `<section>` 块
- 删除图片文件
- 用 `.venv` 安装 mkdocs 依赖,构建并 `gh-deploy`

### 阶段 2:视觉副本排查(关键!)
仅按文件名删除远远不够——微信导出工具常把同一张图存成不同文件名 + 不同格式。
用感知哈希(**dHash**)对全库 **3425 张图片**做视觉比对:

1. 从 git 历史恢复已删侵权图作为比对目标:
   `git show HEAD~1:docs/assets/images/0f56af4996.webp > /tmp/orig.webp`
2. 计算其 dHash(9×8 灰度差分 → 64 bit 指纹)
3. 遍历 `docs/assets/images/` 全部图片计算 dHash
4. 比较汉明距离,`<= 8` 视为疑似同一张

→ 发现副本 `fb78bcf79f.jpg`(距离 2),被引用在 **3 处**(1 中文 + 2 英文,首次处理漏掉了英文版)。全部清除后重新全量扫描:**0 命中**,确认彻底清除。

### 阶段 3:远端配置与部署修正
- 第一次 `gh-deploy` 实际推错仓库了(推到了 `zeropoint5/inchdance`)
- 真正的线上站点仓库是 `inchdance/inchdance.github.io`(纯 `gh-pages` 仓库)
- 切换 `origin` → `inchdance/inchdance.github.io.git`,重新部署

---

## 三、关键经验(重点)

### 1. 删除图片必须查视觉副本,不能只靠文件名
微信导出的 HTML 推文里,同一张图常以 `.jpg / .jpeg / .png / .webp` 多种格式 + 不同 hash 文件名重复存储。**按文件名 `grep` 只能找到一处,必须用视觉哈希全库扫描。** `md5` 在这里无效(不同格式字节不同),必须用 `dHash`/`pHash` 这类感知哈希。

### 2. 中英文版本可能引用不同文件名副本
项目有 `docs/zh/` 和 `docs/en/` 两套(互为翻译)。同一张图在中文版和英文版可能用**不同文件名**的副本。删除时务必同时检查 `zh` 和 `en` 两个目录。

### 3. 部署前务必确认 origin 指向正确的线上仓库
`mkdocs gh-deploy` 推送到 `origin` 的 `gh-pages` 分支。本项目线上仓库是 `inchdance/inchdance.github.io`(GitHub Pages 用户/组织站点,只有 `gh-pages` 分支)。

### 4. SSH 写权限验证
本机 `~/.ssh/id_rsa.pub` 已认证为 GitHub 用户 `zeropoint5`,对 `inchdance` 组织仓库有写权限。
验证写权限(不实际推送):
```bash
git push --dry-run git@github.com:inchdance/inchdance.github.io.git master
```

---

## 四、可复用的排查方法

### 找某张侵权图的所有副本(全库视觉扫描)

```python
from PIL import Image
import hashlib

def dhash(path):
    """9x8 灰度差分哈希 → 64 bit 指纹,跨格式(webp/jpg/png)有效"""
    img = Image.open(path).convert('L').resize((9, 8), Image.LANCZOS)
    px = list(img.getdata())
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (1 if px[r*9+c] > px[r*9+c+1] else 0)
    return bits

def hamming(a, b):
    return bin(a ^ b).count('1')

target = dhash('目标图.webp')
# 遍历 docs/assets/images/ 全部图片,hamming(dhash(f), target) <= 8 视为疑似同一张
```

**距离阈值参考:**
- `0` = 视觉完全一致(仅格式/压缩不同,可确定同一张)
- `1~2` = 极可能同一张
- `> 2` = 待人工确认

### 定位图片引用位置
```bash
grep -rln "文件名" docs/
```

### 统计项目内所有"同图不同名"的冗余
对 `docs/assets/images/` 全量图片两两计算 dHash 汉明距离,用并查集聚类(距离 `<= 6`)。本次在艺术节 13 篇推文引用的 169 张图里就发现 11 组重复。

---

## 五、部署流程(本项目)

### 环境
```bash
python3 -m venv .venv
.venv/bin/pip install mkdocs mkdocs-material "mkdocs-static-i18n[material]" beautifulsoup4
```
> 不需要 `langchain` 等——那些是 `add_post.py` / `llm_html_translator.py` 用的,与构建无关。

### 构建 & 部署
```bash
.venv/bin/mkdocs build --clean           # 本地构建验证
.venv/bin/mkdocs gh-deploy -m "说明"     # 构建 + 推送到 origin/gh-pages
git push origin master                   # 推送源码
```

### 远端配置
| remote | 仓库 | 用途 |
|--------|------|------|
| `origin` | `git@github.com:inchdance/inchdance.github.io.git` | 线上站点(`gh-pages`=网站,`master`=源码) |
| `zeropoint5` | `git@github.com:zeropoint5/inchdance.git` | 备用 |

---

## 六、遗留事项(未处理)

- `mkdocs.yml` 缺 `site_url`,建议补 `site_url: https://inchdance.github.io/`(影响 canonical/sitemap)
- `deploy.sh` 已过时:引用了不存在的 `deploy1` 远端、且调用系统 `mkdocs`(本机未装,实际在 `.venv`)
- `docs/assets/images/` 存在大量"同图不同名"的冗余图片(艺术节推文里就有 11 组),可择机合并清理以减小体积、便于版权排查
