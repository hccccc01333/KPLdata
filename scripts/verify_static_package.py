"""Exercise the actual Windows no-install launcher with external traffic blocked."""
from __future__ import annotations
import argparse, asyncio, hashlib, json, os, re, subprocess, time, urllib.request, zipfile
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
PAGES=[
    ('index.html','#focusHero > *'),
    ('schedule.html','#schBody tr, .day-block, .sched-row'),
    ('teams.html','#teamGrid > *, .tcard, .team-card'),
    ('players.html','#plBody tr, .player, .pl-card'),
    ('heroes.html','#heroGrid > *, .hcard'),
    ('match.html?id=2026062603&g=3&m=13','#rpChart svg'),
    ('game.html?id=1373651472_21_1779526666','#main .panel'),
    ('player.html?id=一诺','#main .panel'),
    ('bp-studio.html?match=2026091201&g=6','#blueLineup > *'),
]

async def validate(folder:Path, output:Path, port:int):
    browser_report=[];blocked=set();errors=[];local_failed=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='msedge',headless=True)
        ctx=await browser.new_context(viewport={'width':1440,'height':960})
        async def route(req):
            if req.request.url.startswith((f'http://127.0.0.1:{port}/','data:','blob:')):await req.continue_()
            else:blocked.add(req.request.url);await req.abort()
        await ctx.route('**/*',route)
        page=await ctx.new_page()
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:local_failed.append({'url':r.url,'status':r.status}) if r.status>=400 and r.url.startswith('http://127.0.0.1:') else None)
        for url,selector in PAGES:
            await page.goto(f'http://127.0.0.1:{port}/'+url,wait_until='networkidle',timeout=60000)
            await page.locator(selector).first.wait_for(timeout=20000)
            if 'match.html?' in url:
                before=await page.locator('#rpRange').input_value()
                await page.evaluate("()=>{let s=document.querySelector('#rpRange');s.value=3;s.dispatchEvent(new Event('input',{bubbles:true}));}")
                await page.wait_for_timeout(200)
                after=await page.locator('#rpRange').input_value()
                if before==after:raise RuntimeError('Replay slider did not change')
            text=await page.locator('body').inner_text()
            if '本地静态快照' not in text:
                print(json.dumps({'page':url,'body_prefix':text[:350],'exceptions':errors,'http_errors':local_failed,'snapshot_script':await page.locator('script[src*="local-snapshot"]').count()},ensure_ascii=True),flush=True)
                await page.screenshot(path=str(output/'failure.png'))
                raise RuntimeError('Local snapshot badge is missing')
            browser_report.append({'url':url,'rendered_selector':selector,'status':'passed'})
            if url.startswith('index.html') or url.startswith('match.html'):
                shot=output/f'offline-{url.split(".")[0]}.png'
                await page.screenshot(path=str(shot),full_page=False)
            print('PASS',url,flush=True)
        # Mobile layout and core replay still work without any third-party connection.
        await page.set_viewport_size({'width':390,'height':844})
        await page.goto(f'http://127.0.0.1:{port}/match.html?id=2026062603&g=3&m=13',wait_until='networkidle')
        await page.locator('#rpChart svg').wait_for()
        overflow=await page.evaluate('document.documentElement.scrollWidth > innerWidth+2')
        browser_report.append({'url':'match.html mobile 390px','status':'failed' if overflow else 'passed','horizontal_overflow':overflow})
        await browser.close()
    report={'status':'passed' if not errors and not local_failed and not overflow else 'failed','launcher':'Windows PowerShell 5, System.Net.Sockets.TcpListener; no Python/Node/model used by launcher','network':'all browser requests outside 127.0.0.1 blocked','scope':'core historical querying, data rendering and replay interaction; not live collection, model training or external video playback','snapshot':str(folder.resolve()),'pages':browser_report,'uncaught_exceptions':errors,'local_http_errors':local_failed,'blocked_external_requests':len(blocked),'external_image_caveat':'External images were intentionally blocked; they are not required for local chart/data use.'}
    (output/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if report['status']!='passed':raise RuntimeError(json.dumps(report,ensure_ascii=True))
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--port',type=int,default=0);args=ap.parse_args()
    folder=args.folder.resolve();output=folder.parent/(folder.name+'-checks');output.mkdir(exist_ok=True)
    browser_temp=output/'browser-temp';browser_temp.mkdir(exist_ok=True)
    os.environ['TEMP']=str(browser_temp);os.environ['TMP']=str(browser_temp)
    archive=folder.with_suffix('.zip')
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise RuntimeError('Corrupt ZIP entry')
    binary=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    server=subprocess.Popen([str(binary),'-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',str(folder/'start.ps1'),'-NoBrowser','-Port',str(args.port)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        line=server.stdout.readline().decode('utf-8',errors='replace')
        match=re.search(r'http://127\.0\.0\.1:(\d+)/',line)
        if not match:raise RuntimeError('Launcher did not report its bound URL: '+line)
        port=int(match.group(1))
        for _ in range(40):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=.5) as r:
                    actual=r.read()
                    if r.status==200 and actual==(folder/'site/index.html').read_bytes():break
            except Exception:
                if server.poll() is not None:raise RuntimeError(server.communicate()[1].decode(errors='replace'))
                time.sleep(.25)
        else:raise RuntimeError('Launcher did not serve HTTP')
        report=asyncio.run(validate(folder,output,port))
        print(json.dumps({'status':report['status'],'report':str(output/'verification.json'),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},ensure_ascii=True))
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill()

if __name__=='__main__':main()
