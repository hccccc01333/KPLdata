"""Bundle only the public static product, with a no-install Windows launcher."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--site',type=Path,default=ROOT.parent/'kpl-data-center-site')
    ap.add_argument('--stamp',default=datetime.now().strftime('%Y%m%d-%H%M%S'))
    args=ap.parse_args()
    source=args.site.resolve()
    destination=ROOT/'distribution'/f'kpl-insight-static-{args.stamp}'
    if destination.exists():raise SystemExit('Choose a new --stamp; existing packages are preserved.')
    site=destination/'site';site.mkdir(parents=True)
    files=[*source.glob('*.html'),*(p for p in (source/'assets').rglob('*') if p.is_file())]
    allowed={'.html','.js','.json','.css','.png','.jpg','.jpeg','.svg','.webp','.woff2','.ico'}
    manifest=[]
    for file in files:
        relative=file.relative_to(source)
        if file.suffix.lower() not in allowed or any(x.startswith('.') for x in relative.parts):continue
        target=site/relative;target.parent.mkdir(parents=True,exist_ok=True)
        data=file.read_bytes()
        if file.suffix in {'.html','.js','.css','.json'}:
            text=data.decode('utf-8-sig')
            if file.suffix=='.html' or relative.as_posix()=='assets/common.js':
                text=text.replace('KPL 数据中心','峡谷有数').replace('https://github.com/hccccc01333/KPLdata"','https://github.com/hccccc01333/kpl-insight"')
            if file.suffix=='.html':
                text=text.replace('</head>','<script defer src="assets/local-snapshot.js"></script>\n</head>')
            data=text.encode('utf-8')
        target.write_bytes(data)
        manifest.append({'path':relative.as_posix(),'source_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'packaged_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    # Snapshot identity is visible in the product, rather than masquerading as live data.
    info="""document.addEventListener('DOMContentLoaded',function(){
var note=document.createElement('div');
note.textContent='本地静态快照 · 2026-10-23 · 数据不会自动更新 · 原始比赛录像和外部图片仍需联网';
note.style.cssText='padding:8px 16px;text-align:center;background:#f4f0e4;color:#55492e;font:12px/1.6 system-ui,sans-serif;border-bottom:1px solid #ded7c5';
document.body.insertBefore(note,document.body.firstChild);
});
"""
    (site/'assets/local-snapshot.js').write_text(info,encoding='utf-8')
    shutil.copyfile(ROOT/'scripts/static_site_launcher.ps1',destination/'start.ps1')
    launcher='@echo off\r\ncd /d "%~dp0"\r\n"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"\r\nif errorlevel 1 pause\r\n'
    (destination/'启动网站.bat').write_bytes(launcher.encode('gbk'))
    instructions='''# 峡谷有数 · 静态网站体验包

## Windows：解压后双击，无需 Python、Node 或模型

1. 把整个 ZIP 解压到一个普通文件夹，保留 site、start.ps1 和启动网站.bat 的相对位置。
2. 双击“启动网站.bat”。默认浏览器会打开本地网站。
3. 使用期间保留启动窗口，浏览完关闭该窗口即可停止。服务仅监听本机 127.0.0.1，无需管理员权限。

不要只从压缩包中拖出一个 HTML，也不要直接双击 site/index.html：部分比赛数据需要通过本地 HTTP 加载。

## 包含什么

这是 2026-10-23 的产品快照：赛程比分、战队/选手/英雄统计、已有快照的比赛复盘、实时预测历史归档，以及 BP、对比等页面。网页、脚本、字体和处理后的展示数据已包含在包内，不需要连接海外网站即可加载核心查询与图表。

这是静态快照，不是持续运行的采集服务；不会自动更新比赛日数据，也不会启动训练或声称正在直播。选手/英雄图片、原始比赛录像、官方站和 GitHub 链接仍属于联网资源；核心查询和已有比赛图表可在不加载这些外部资源时使用。

## macOS / Linux 或已有 Python 的用户

在 site 目录运行 `python3 -m http.server 8000 --bind 127.0.0.1`，打开 http://127.0.0.1:8000 。

## 交流与开发

项目：https://github.com/hccccc01333/kpl-insight
站点源码：https://github.com/hccccc01333/KPLdata-site

本包不含原始接口响应、完整采集快照、预训练模型或真实比赛视频。原创代码与文档按 MIT 许可；赛事数据、商标、图片等第三方资源归各自权利人所有。
'''
    (destination/'使用说明.md').write_text(instructions,encoding='utf-8-sig')
    (destination/'LICENSE').write_bytes((ROOT/'LICENSE').read_bytes())
    record={'snapshot_date':'2026-10-23','created_at':datetime.now().astimezone().isoformat(),'source':str(source),'mode':'static snapshot; no live collection or model runtime','files':manifest}
    (destination/'snapshot-manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=destination.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in destination.rglob('*'):
            if file.is_file():z.write(file,file.relative_to(destination.parent))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.sha256').write_text(f'{digest}  {archive.name}\n',encoding='ascii')
    print(json.dumps({'folder':str(destination),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest,'public_files':len(manifest)},ensure_ascii=True))

if __name__=='__main__':main()
