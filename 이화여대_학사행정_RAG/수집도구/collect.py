#!/usr/bin/env python3
"""Public Ewha academic corpus collection, resumable SQLite frontier.

Uses curl's system trust store, lxml and the bundled document parsers.
Never authenticates, writes to remote sites, or bypasses robots/access controls.
"""
import argparse, concurrent.futures, copy, hashlib, html as htmlmod, json, logging
import mimetypes, os, re, sqlite3, subprocess, tempfile, threading, time
import urllib.parse as U, urllib.robotparser, zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from lxml import html, etree

ROOT = Path(__file__).resolve().parents[1]
UA = 'EwhaAcademicResearchCollector/0.1'
TZ = ZoneInfo('Asia/Seoul')
LOCK = threading.RLock()
HOST_LOCKS, HOST_LAST, ROBOTS = {}, {}, {}
POS = re.compile(r'학사|학칙|규정|등록|휴학|복학|수강|성적|학점|졸업|수료|논문|학위|전공|전과|장학|대출|증명|학생증|출석|교육과정|교과과정|교과목|교직|자격|계절|재입학|제적|자퇴|교류|교환|기숙|입사|퇴사|서식|양식|FAQ|자주|매뉴얼|신입생|편입|학적|연구윤리|학사경고|학적|현장실습|인턴|장애학생|대학원|유레카|포털|포탈|공지|notice|academic|curricul|scholar|graduate|student|form|rule|faq|manual|regist|calendar|credit|course|thesis|degree|dorm|certificate|support|license|intern|enroll|grade|major|schoollife|life|international|exchange', re.I)
NEG = re.compile(r'교수채용|교원채용|직원채용|교수진|교원인사|교수소개|인사말|연혁|교수업적|연구실소개|논문실적|입찰|일반경쟁|공사/|기계/|규격사양|연구성과|홍보영상|기부|동창|학술대회|세미나|심포지엄|사진첩|갤러리|photo|gallery|professor|alumni|giving|research-publication', re.I)
POS = re.compile(POS.pattern + r'|연락처|담당업무|전화번호|행정실|contact|office', re.I)
PROF_PATH = re.compile(r'[-_]prof(?:\.|/|[-_])|/professor/|/publications?/|/~',re.I)
PRIVATE = re.compile(r'(?:login|logout|sign[-_]?in|auth/|sso|(?:mode|mod|command|action)=(?:write|edit|editor|delete|remove|modify|save|reply)(?:&|$)|/qna|/q-and-a|/qanda|admission/qna|password|member/)', re.I)
BAD_HOSTS = {'portal.ewha.ac.kr','eureka.ewha.ac.kr','cyber.ewha.ac.kr','parent.ewha.ac.kr','giving.ewha.ac.kr','the.ewha.ac.kr','admission.ewha.ac.kr'}
FILE_EXT = {'.pdf','.hwp','.hwpx','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.txt','.zip'}
DIR_URLS = {'https://www.ewha.ac.kr/ewha/academics/college.do','https://www.ewha.ac.kr/ewha/intro/organ02.do','https://www.ewha.ac.kr/ewha/intro/organ03.do'}
DROP_QUERY = {'utm_source','utm_medium','utm_campaign','fbclid'}
DB = None
_prof_file=ROOT/'01_출처목록/개인_교수사이트_제외목록.jsonl'
PERSONAL_ROOTS=[json.loads(s) for s in _prof_file.read_text().splitlines()] if _prof_file.exists() else []

def now(): return datetime.now(TZ).isoformat(timespec='seconds')
def jdump(v): return json.dumps(v, ensure_ascii=False)
def key(url): return hashlib.sha256(url.encode()).hexdigest()[:24]
def normalize(url, base=''):
    url = htmlmod.unescape(U.urljoin(base, url.strip()))
    p = U.urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname: return None
    if p.username or p.password: return None
    q = [(k,v) for k,v in U.parse_qsl(p.query, keep_blank_values=True) if k not in DROP_QUERY]
    if any(k=='command' and v=='view2' for k,v in q) and any(k=='boardSeq' for k,v in q):
        q=[(k,v) for k,v in q if k not in {'page','pageNo','pageIndex'}]
    if any(k.lower() == 'mode' and v in ('view','download','view-rule') for k,v in q):
        q = [(k,v) for k,v in q if k not in {'article.offset','articleOffset','articleLimit','page','pageNo','pageIndex'}]
        if any(k=='articleNo' for k,v in q): q=[(k,v) for k,v in q if k!='no']
    netloc=p.netloc.lower()
    if p.scheme=='https' and netloc.endswith(':443'): netloc=netloc[:-4]
    path=U.quote(U.unquote(p.path or '/'),safe='/!$&\'()*+,-.:;=@_~')
    return U.urlunsplit((p.scheme,netloc,path,U.urlencode(sorted(q)),''))

def official(url):
    host = U.urlsplit(url).hostname or ''
    return host.endswith('.ewha.ac.kr') or host == 'ewha.ac.kr' or host in {'www.ewhamed.ac.kr','ewhamed.ac.kr'}

def sql(statement,args=()):
    with LOCK:
        out=DB.execute(statement,args)
        DB.commit()
        return out

def enqueue(url, parent=None, label='', priority=5, reason='linked', force=False):
    url=normalize(url,parent or '')
    if not url: return
    host=U.urlsplit(url).hostname
    excluded = None
    if not official(url): excluded='external_reference'
    elif host in BAD_HOSTS or PRIVATE.search(url): excluded='private_or_out_of_scope'
    elif any(host==o['host'] and U.urlsplit(url).path.startswith(o['prefix']) for o in PERSONAL_ROOTS):excluded='faculty_personal_site_outside_scope'
    elif '/ewha/life/restaurant.do' in U.urlsplit(url).path and U.urlsplit(url).query: excluded='daily_menu_outside_student_administration'
    elif re.search(r'/bachelor/calendar\d{4}\.do',U.urlsplit(url).path):
        cp=U.urlsplit(url);cq=U.parse_qs(cp.query);py=re.search(r'calendar(\d{4})',cp.path).group(1)
        cy=str(datetime.now(TZ).year)
        if cq.get('mode')==['user_calendar']:excluded='monthly_presentation_annual_source_kept'
        elif cq.get('year') and cq['year'][0]!=py and not (py==cy and cq['year'][0]==str(int(cy)+1)):excluded='redundant_or_unpublished_calendar_route_official_year_list_kept'
    elif PROF_PATH.search(U.urlsplit(url).path): excluded='faculty_profile_outside_scope'
    elif NEG.search(label+' '+U.urlsplit(url).path) and not force: excluded='non_student_administration'
    if U.urlsplit(url).path.lower().endswith(('.png','.jpg','.jpeg','.gif','.svg','.mp4','.mp3','.woff','.css')) and not force:
        excluded='presentation_asset'
    status = 'excluded' if excluded else 'pending'
    with LOCK:
        DB.execute('INSERT OR IGNORE INTO frontier(url,host,parent,label,priority,status,reason,created_at) VALUES(?,?,?,?,?,?,?,?)',(url,host,parent,label,priority,status,excluded or reason,now()))
        if parent: DB.execute('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',(parent,url,label,excluded or reason))
        DB.commit()

def curl_once(url):
    host=U.urlsplit(url).hostname
    with LOCK: hostlock=HOST_LOCKS.setdefault(host,threading.Lock())
    with hostlock:
        delay=max(2.0, ROBOTS.get(host,{}).get('delay',2.0))
        time.sleep(max(0,delay-(time.monotonic()-HOST_LAST.get(host,0))))
        HOST_LAST[host]=time.monotonic()
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'body'; hdr=Path(td)/'headers'
            proc=subprocess.run(['curl','-sS','--globoff','--max-time','90','--connect-timeout','12','--max-filesize','524288000','-A',UA,'-D',str(hdr),'-o',str(out),'-w','%{json}',url],capture_output=True)
            try: meta=json.loads(proc.stdout)
            except Exception: meta={}
            header=hdr.read_text(errors='replace') if hdr.exists() else ''
            body=out.read_bytes() if out.exists() else b''
            return {'status':int(meta.get('http_code',0)), 'headers':header,'body':body,'content_type':meta.get('content_type',''),'error':proc.stderr.decode(errors='replace').strip(),'exit_code':proc.returncode}

def ensure_robots(url):
    host=U.urlsplit(url).hostname
    with LOCK:
        if host in ROBOTS: return ROBOTS[host]
    result=curl_once(f'{U.urlsplit(url).scheme}://{host}/robots.txt')
    body=result['body'].decode('utf-8',errors='replace')
    parser=urllib.robotparser.RobotFileParser()
    valid = result['status']==200 and not re.search(r'<html|<!doctype',body,re.I)
    if valid: parser.parse(body.splitlines())
    state={'status':result['status'],'retrieved_at':now(),'parser':parser if valid else None,'delay':parser.crawl_delay(UA) or parser.crawl_delay('*') or 2,'policy': 'parsed' if valid else 'not_provided' if result['status'] in (404,410) else 'unavailable_or_non_robot_response','blocked_all':result['status'] in (401,403),'error':result['error']}
    policy_dir=ROOT/'01_출처목록'/'접근정책';policy_dir.mkdir(parents=True,exist_ok=True)
    (policy_dir/f'{host}.txt').write_text(body,encoding='utf-8')
    with LOCK: ROBOTS[host]=state
    sql('INSERT OR REPLACE INTO policies VALUES(?,?)',(host,jdump({k:v for k,v in state.items() if k!='parser'})))
    return state

def fetch(url):
    original=url
    for hop in range(8):
        if not official(url) or U.urlsplit(url).hostname in BAD_HOSTS or PRIVATE.search(url):
            return {'status':0,'body':b'','headers':'','error':'redirect_outside_public_scope','final_url':url,'collection_status':'restricted'}
        pol=ensure_robots(url)
        if pol['blocked_all'] or (pol['parser'] and not pol['parser'].can_fetch(UA,url)):
            return {'status':0,'body':b'','headers':'','error':'robots_disallowed','final_url':url,'collection_status':'restricted'}
        result=curl_once(url)
        if result['status']==429 or result['status'] in (502,503,504):
            retry=re.search(r'(?im)^retry-after:\s*(\d+)',result['headers'])
            time.sleep(min(60,int(retry.group(1)) if retry else 15))
            result=curl_once(url)
        if result['status'] in (301,302,303,307,308):
            location=re.search(r'(?im)^location:\s*(.+)',result['headers'])
            if location:
                url=normalize(location.group(1).strip(),url)
                if url: continue
        result['final_url']=url
        result['collection_status']='collected' if 200 <= result['status'] < 300 and result['body'] and result['exit_code']==0 else 'failed'
        return result
    return {'status':0,'body':b'','headers':'','error':'redirect_loop','final_url':original,'collection_status':'failed'}

def decode(body):
    enc=re.search(br'(?:charset\s*=\s*["\']?)([\w-]+)',body[:10000],re.I)
    encoding=enc.group(1).decode('ascii') if enc else 'utf-8'
    try: return body.decode(encoding)
    except (UnicodeDecodeError,LookupError):
        try: return body.decode('cp949')
        except UnicodeDecodeError: return body.decode('utf-8',errors='replace')

def clean_text(node):
    node=copy.deepcopy(node)
    for e in node.xpath('.//script|.//style|.//noscript|.//header|.//footer|.//nav|.//form[@id="searchForm"]'):
        e.drop_tree()
    for e in node.xpath('.//br'): e.tail='\n'+(e.tail or '')
    for e in node.xpath('.//p|.//li|.//h1|.//h2|.//h3|.//h4|.//h5|.//h6|.//tr|.//div'): e.tail='\n'+(e.tail or '')
    for e in node.xpath('.//td|.//th'): e.tail='\t'+(e.tail or '')
    return '\n'.join(line.strip() for line in node.text_content().splitlines() if line.strip())

def main_node(tree):
    for xp in ['//*[@id="jwxe_main_content"]','//*[contains(concat(" ",normalize-space(@class)," ")," board-view ")]','//*[contains(@class,"b-view-box")]','//*[@id="contents"]','//*[@id="content"]','//main','//*[contains(@class,"content-wrap")]','//*[contains(@class,"content-box")]','//body']:
        nodes=tree.xpath(xp)
        if nodes: return nodes[0],xp
    return tree,'whole_document'

def label_of(a): return re.sub(r'\s+',' ',' '.join(a.itertext())).strip() or a.get('title','')

def org_entry(a,base):
    url=normalize(a.get('href',''),base)
    if not url or not official(url) or U.urlsplit(url).hostname in BAD_HOSTS: return
    context=a
    for _ in range(5):
        if context.getparent() is None: break
        context=context.getparent()
        if context.xpath('.//h3|.//h4|.//h5|.//*[contains(@class,"title")]'): break
    names=context.xpath('.//h3//text()|.//h4//text()|.//h5//text()|.//*[contains(@class,"title")]//text()')
    explicit=a.get('title','')
    name=(re.sub(r'\s*홈페이지.*','',explicit).strip() if '홈페이지' in explicit and '대학' in explicit else '') or ' '.join(x.strip() for x in names if x.strip())[:180] or explicit or label_of(a)
    sql('INSERT INTO organizations VALUES(?,?,?,?) ON CONFLICT(url) DO UPDATE SET name=excluded.name,parent=excluded.parent',(url,name,base,now()))
    enqueue(url,base,name,1,'official_organization',True)

def discover(tree,node,base,item,text):
    ismain=U.urlsplit(base).hostname in ('www.ewha.ac.kr','ewha.ac.kr')
    is_directory=(base.split('?')[0] in DIR_URLS or '/ewha/academics/' in base) and not PROF_PATH.search(base)
    if is_directory:
        for a in tree.xpath('//a[contains(@class,"b-home")]'): org_entry(a,base)
    # Official related-site menus enumerate colleges/graduate schools, including legacy URLs.
    if ismain:
        for a in tree.xpath('//a[@href and contains(@title,"홈페이지 새창")]'):
            if re.search(r'대학|대학원|학부|학과',a.get('title','')+label_of(a)): org_entry(a,base)
    candidates=tree.xpath('//a[@href]')
    annual_calendar=bool(node.xpath('.//*[contains(@class,"b-cal-list-box")]'))
    annual_has_events=bool(node.xpath('.//*[contains(@class,"b-cal-list-box")]//li'))
    baseq=U.parse_qs(U.urlsplit(base).query)
    is_view=('mode=view' in base and 'view-rule' not in base) or (baseq.get('command')==['view2'] and 'boardSeq' in baseq) or (baseq.get('mod')==['document'] and 'uid' in baseq)
    for a in candidates:
        href=a.get('href','').strip(); label=label_of(a)
        if href.startswith(('javascript:','#','mailto:','tel:')):
            if href.startswith('javascript:') and POS.search(label):
                sql('INSERT OR IGNORE INTO review VALUES(?,?,?)',(base,'javascript_link',label+' '+href))
            continue
        url=normalize(href,base)
        if not url or url==base: continue
        path=U.urlsplit(url).path; query=U.urlsplit(url).query
        calendar_query=U.parse_qs(query)
        if path==U.urlsplit(base).path and calendar_query.get('year') and re.search(r'이전|다음|prev|next',label,re.I) and re.search(r'등록된\s*일정이\s*없|일정이\s*없습니다|no\s+(?:events|schedules)',text,re.I):
            sql('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',(base,url,label,'empty_schedule_has_no_further_published_year_data'))
            continue
        if annual_calendar and path==U.urlsplit(base).path:
            reason=None
            if calendar_query.get('mode') in (['calendar'],['user_calendar']):reason='monthly_presentation_annual_source_kept'
            elif calendar_query.get('year') and (not annual_has_events or int(calendar_query['year'][0])>datetime.now(TZ).year+1) and re.search(r'이전|다음|prev|next',label,re.I):reason='empty_or_unpublished_calendar_navigation'
            if reason:
                sql('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',(base,url,label,reason))
                continue
        attachment='mode=download' in query or 'filedownload' in path.lower() or Path(path).suffix.lower() in FILE_EXT
        within_body = a is node or node in a.iterancestors()
        if attachment:
            ancestors=list(a.iterancestors())
            row=next((e for e in ancestors if e.tag in ('tr','li')),a.getparent() if a.getparent() is not None else a)
            context=label_of(row)
            if within_body and not NEG.search(context): enqueue(url,base,label,2,'attachment',True)
            elif within_body: sql('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',(base,url,label,'attachment_of_out_of_scope_notice'))
            continue
        if 'mode=view-rule' in query:
            if re.search(r'학칙|학사|학생|성적|장학|교직|국제교류|학적|수업|졸업|학점|기숙|장애|등록|논문|대학원|도서관|증명',label): enqueue(url,base,label,2,'rule',True)
            else:
                sql('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',(base,url,label,'rule_outside_student_scope'))
            continue
        if ismain:
            if path.startswith('/ewha/bachelor/'):
                enqueue(url,base,label,2 if not query else 6,'academic_menu')
            elif path.startswith('/ewha/life/'):
                enqueue(url,base,label,4,'student_service')
            elif path.startswith('/ewha/academics/') and not PROF_PATH.search(path) and not NEG.search(path+' '+label):
                enqueue(url,base,label,1,'organization_directory')
            elif path in ('/ewha/intro/organ02.do','/ewha/intro/organ03.do','/ewha/intro/organ-popup.do','/ewha/intro/phone.do','/ewha/intro/rules.do','/ewha/guide/sitemap.do'):
                if not is_view: enqueue(url,base,label,1,'official_directory')
            elif '/ewha/news/notice.do' in path and within_body:
                if 'articleNo=' in query:
                    if POS.search(label) and not NEG.search(label): enqueue(url,base,label,6,'academic_notice')
                    else: sql('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',(base,url,label,'notice_outside_scope_or_review'))
                elif not is_view: enqueue(url,base,label,7,'notice_listing')
            elif path.startswith('/_res/ewha/etc/iEwha/') or 'sitemap' in path or path=='/ewha/ewha.xml': enqueue(url,base,label,1,'ebook_or_sitemap',True)
            elif official(url) and U.urlsplit(url).hostname!='www.ewha.ac.kr' and POS.search(label):
                enqueue(url,base,label,3,'official_service_link')
        else:
            host=U.urlsplit(url).hostname
            samehost=host==U.urlsplit(base).hostname
            uq=U.parse_qs(query)
            if samehost and path.endswith('boardList.action') and 'boardId' in uq and 'boardSeq' not in uq and not is_view:
                enqueue(url,base,label,7,'legacy_board_pagination',True)
            elif 'articleNo=' in query or 'b_seq=' in query or 'wr_id=' in query or ('boardSeq' in uq and uq.get('command')==['view2']) or ('uid' in uq and uq.get('mod')==['document']):
                if within_body and POS.search(label+' '+item['label']) and not NEG.search(label): enqueue(url,base,label,6,'institution_notice')
                else: sql('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',(base,url,label,'notice_outside_scope_or_review'))
            elif samehost and (POS.search(path+' '+label) or (within_body and attachment)) and not NEG.search(path+' '+label):
                if not is_view or 'mode=list' not in query: enqueue(url,base,label,4 if not query else 7,'institution_menu')
            elif official(url) and POS.search(label) and not NEG.search(label): enqueue(url,base,label,4,'official_cross_reference')
    # Embedded public documents and FAQ endpoint links.
    for e in tree.xpath('//frame[@src]|//iframe[@src]|//embed[@src]|//object[@data]'):
        enqueue(e.get('src') or e.get('data'),base,'embedded public document',2,'embedded',True)
    for e in tree.xpath('//meta[translate(@http-equiv,"REFSH","refsh")="refresh"]'):
        m=re.search(r'url\s*=\s*(.+)',e.get('content',''),re.I)
        if m: enqueue(m.group(1).strip('"\' '),base,item['label'],1,'public_meta_redirect',True)
    if is_view or '/notice/' in U.urlsplit(base).path:
        for e in node.xpath('.//img[@src or @data-src]'):
            src=e.get('data-src') or e.get('src') or ''
            if not re.search(r'logo|icon|btn_|arrow|spacer|blank|avatar|^data:',src,re.I):
                enqueue(src,base,'본문 이미지: '+item['label'],2,'notice_body_image',True)

def parse_html(body,item,final):
    decoded=decode(body); tree=html.fromstring(decoded,base_url=final)
    page_title=' '.join(tree.xpath('//title/text()')).strip() or item['label']
    title=page_title
    node,selector=main_node(tree)
    textnode=node
    fq=U.parse_qs(U.urlsplit(final).query)
    if 'mode=view' in final or (fq.get('command')==['view2'] and 'boardSeq' in fq) or (fq.get('mod')==['document'] and 'uid' in fq):
        titles=node.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," b-title ")]|.//*[contains(concat(" ",normalize-space(@class)," ")," kboard-title ")]')
        title=label_of(titles[0]) if titles else item['label'] or page_title
        actual=node.xpath('.//*[contains(@class,"b-content-box")]//*[contains(@class,"fr-view")]|.//*[contains(@class,"b-content-box")]|.//*[contains(@class,"kboard-content")]//*[contains(@class,"content-view")]')
        if actual: textnode=actual[0]
    text=clean_text(textnode)
    content_hash=hashlib.sha256(text.encode()).hexdigest()
    doc={'title':title,'page_title':page_title,'text':text,'selector':selector,'headings':[' '.join(e.itertext()).strip() for e in node.xpath('.//h1|.//h2|.//h3|.//h4|.//h5')], 'tables':[[[label_of(c) for c in row.xpath('./th|./td')] for row in table.xpath('.//tr')] for table in node.xpath('.//table')], 'links':[{'label':label_of(a),'url':normalize(a.get('href',''),final)} for a in node.xpath('.//a[@href]')], 'parse_status':'draft_text' if len(text)>40 else 'needs_dynamic_or_ocr','body_hash':content_hash}
    if re.search(r'로그인이 필요|로그인 후 이용|권한이 없습니다|접근 권한이|비밀글입니다',text): doc['parse_status']='access_restricted_content'
    if '홈페이지 점검 중' in text and len(text)<500: doc['parse_status']='site_error_content'
    if doc['parse_status']=='needs_dynamic_or_ocr': sql('INSERT OR IGNORE INTO review VALUES(?,?,?)',(item['url'],'empty_or_dynamic',title))
    with LOCK:
        duplicates=DB.execute('SELECT url FROM content_hashes WHERE hash=? AND url!=? LIMIT 1',(content_hash,item['url'])).fetchone()
    sql('INSERT OR IGNORE INTO content_hashes VALUES(?,?,?)',(content_hash,item['url'],selector))
    if duplicates:
        doc['duplicate_body_of']=duplicates[0]
        if re.search(r'(?:article.offset|page|pageNo|pageIndex|pageNum|page_idx|cpage)=',item['url']):
            sql('INSERT OR IGNORE INTO review VALUES(?,?,?)',(item['url'],'repeated_listing_body',duplicates[0]))
        else: discover(tree,node,final,item,text)
    else: discover(tree,node,final,item,text)
    return doc

def extension(body,ctype,headers,url):
    if body.startswith(b'%PDF'): return '.pdf'
    if body.startswith(b'\xff\xd8\xff'): return '.jpg'
    if body.startswith(b'\x89PNG\r\n\x1a\n'): return '.png'
    if body.startswith((b'GIF87a',b'GIF89a')): return '.gif'
    if body.startswith(b'BM'): return '.bmp'
    if body.startswith(b'\xd0\xcf\x11\xe0'): return '.hwp' if 'hwp' in headers.lower() else '.ole'
    disp=re.search(r'(?i)filename\*?\s*=\s*([^\r\n;]+)',headers)
    if disp:
        name=U.unquote(disp.group(1)).strip('"\' ')
        suffix=Path(name).suffix.lower()
        if suffix: return suffix
    if body.startswith(b'PK'):
        try:
            import io
            names=zipfile.ZipFile(io.BytesIO(body)).namelist()
            if any(s.startswith('word/') for s in names): return '.docx'
            if any(s.startswith('xl/') for s in names): return '.xlsx'
            if any(s.startswith('Contents/section') for s in names): return '.hwpx'
        except Exception: pass
        return '.zip'
    if body.lstrip().startswith(b'<?xml'): return '.xml'
    if 'html' in (ctype or '') or re.search(br'<(?:!doctype html|html)',body[:1000],re.I): return '.html'
    return Path(U.urlsplit(url).path).suffix.lower() or '.bin'

def process(item):
    result=fetch(item['url']); body=result['body']; final=result['final_url']
    docid=key(item['url']); ctype=result.get('content_type') or ''
    ext=extension(body,ctype,result['headers'],final)
    rawrel=None; doc=None
    if body:
        sha=hashlib.sha256(body).hexdigest()
        directory=ROOT/'02_원본'/U.urlsplit(final).hostname; directory.mkdir(parents=True,exist_ok=True)
        target=directory/(docid+'_'+sha[:12]+ext);target.write_bytes(body)
        rawrel=str(target.relative_to(ROOT))
        target.with_suffix(target.suffix+'.headers.txt').write_text(result['headers'],encoding='utf-8')
        if result['collection_status']=='collected':
            if ext=='.html':
                try: doc=parse_html(body,item,final)
                except Exception as exc: doc={'parse_status':'parse_error','error':str(exc)}
            elif ext=='.xml' or 'sitemap' in item['url'] or item['url'].endswith('.xml'):
                try:
                    xml=etree.fromstring(body)
                    locs=xml.xpath('//*[local-name()="loc"]/text()')
                    for loc in locs:
                        norm=normalize(loc,final)
                        if norm and (norm.endswith('/ewha/ewha.xml') or norm.endswith('/board/board.xml') or '/ewha/bachelor/' in norm or '/ewha/life/' in norm or '/ewha/academics/' in norm): enqueue(norm,final,'sitemap entry',1,'sitemap',True)
                    doc={'title':'sitemap','text':'\n'.join(locs),'parse_status':'discovery_only','entry_count':len(locs)}
                except Exception as exc: doc={'parse_status':'parse_error','error':str(exc)}
            else:
                from attachments import extract
                try:
                    doc=extract(target,ext);doc['title']=item['label']
                    if doc.get('parse_status') in ('needs_ocr','preview_only','unsupported_attachment','unsupported_ole_attachment','archive_inventory_only'):
                        sql('INSERT OR IGNORE INTO review VALUES(?,?,?)',(item['url'],doc['parse_status'],item['label']))
                except Exception as exc:
                    doc={'title':item['label'],'parse_status':'attachment_parse_error','error':str(exc)}
    record={'doc_id':docid,'school_id':'ewha','source_url':item['url'],'final_url':final,'parent_url':item['parent'],'title':item['label'],'collected_at':now(),'http_status':result['status'],'collection_status':result['collection_status'],'content_type':ctype,'format':ext,'raw_path':rawrel,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest() if body else None,'error':result['error'],'rights_status':'unverified','applicability_status':'unknown'}
    if doc:
        if doc.get('parse_status') in ('site_error_content','access_restricted_content'):
            record['collection_status']='restricted' if doc['parse_status']=='access_restricted_content' else 'failed'
            record['error']=doc['parse_status']
        if doc.get('error'): doc['parse_error']=doc.pop('error')
        record.update(doc)
        parsed=ROOT/'03_정제문서'/'문서별';parsed.mkdir(parents=True,exist_ok=True)
        (parsed/(docid+'.json')).write_text(jdump(record),encoding='utf-8')
    with LOCK:
        DB.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',(item['url'],record['collection_status'],jdump(record)))
        DB.execute('UPDATE frontier SET status=?, finished_at=?, final_url=? WHERE url=?',(record['collection_status'],now(),final,item['url']))
        if final!=item['url']:
            DB.execute('UPDATE frontier SET status="alias_collected",final_url=? WHERE url=? AND status="pending"',(final,final))
        DB.commit()
    return record

def export():
    with LOCK:
        frontier=[dict(r) for r in DB.execute('SELECT * FROM frontier ORDER BY priority,url')]
        docs=[json.loads(r[0]) for r in DB.execute('SELECT data FROM documents')]
        orgs=[dict(r) for r in DB.execute('SELECT * FROM organizations')]
        reviews=[dict(r) for r in DB.execute('SELECT * FROM review')]
        edges=[dict(r) for r in DB.execute('SELECT * FROM edges')]
    for rel,rows in [('01_출처목록/source_registry.jsonl',frontier),('01_출처목록/조직_사이트_목록.jsonl',orgs),('01_출처목록/출처_연결관계.jsonl',edges),('02_원본/crawl_manifest.jsonl',docs),('03_정제문서/parsed_documents.jsonl',[d for d in docs if d.get('text')]),('07_수집보고서/review_queue.jsonl',reviews)]:
        p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(''.join(jdump(r)+'\n' for r in rows),encoding='utf-8')
    stats={'updated_at':now(),'frontier':dict(Counter(r['status'] for r in frontier)),'documents':len(docs),'formats':dict(Counter(r['format'] for r in docs if r['collection_status']=='collected')),'organizations':len(orgs),'hosts':len({r['host'] for r in frontier if r['status']!='excluded'}),'raw_bytes':sum(r['bytes'] for r in docs),'review_items':len(reviews),'parse_status':dict(Counter(r.get('parse_status','unparsed') for r in docs))}
    (ROOT/'07_수집보고서'/'progress.json').write_text(jdump(stats),encoding='utf-8')
    return stats

def init():
    global DB
    for dirname in ['01_출처목록','02_원본','03_정제문서','04_구조화정보','05_검색청크','06_벡터DB','07_수집보고서']: (ROOT/dirname).mkdir(exist_ok=True)
    DB=sqlite3.connect(ROOT/'01_출처목록'/'collection.sqlite3',check_same_thread=False)
    DB.row_factory=sqlite3.Row
    DB.executescript('''PRAGMA journal_mode=WAL;
      CREATE TABLE IF NOT EXISTS frontier(url TEXT PRIMARY KEY,host TEXT,parent TEXT,label TEXT,priority INTEGER,status TEXT,reason TEXT,created_at TEXT,finished_at TEXT,final_url TEXT);
      CREATE TABLE IF NOT EXISTS documents(url TEXT PRIMARY KEY,status TEXT,data TEXT);
      CREATE TABLE IF NOT EXISTS edges(parent TEXT,url TEXT,label TEXT,reason TEXT,PRIMARY KEY(parent,url,label));
      CREATE TABLE IF NOT EXISTS organizations(url TEXT PRIMARY KEY,name TEXT,parent TEXT,discovered_at TEXT);
      CREATE TABLE IF NOT EXISTS policies(host TEXT PRIMARY KEY,data TEXT);
      CREATE TABLE IF NOT EXISTS review(url TEXT,reason TEXT,detail TEXT,PRIMARY KEY(url,reason,detail));
      CREATE TABLE IF NOT EXISTS content_hashes(hash TEXT,url TEXT,selector TEXT,PRIMARY KEY(hash,url));
    ''')
    sql('UPDATE frontier SET status="pending" WHERE status="running"')
    seeds=json.loads((ROOT/'00_계획'/'확장_출처목록.json').read_text())['sources']
    for s in seeds: enqueue(s['url'],label=s['title'],priority=s['priority'],reason='planned_seed',force=True)

def reparse_existing():
    from attachments import extract
    rows=[dict(r) for r in DB.execute('SELECT * FROM documents WHERE status="collected"')]
    for row in rows:
        d=json.loads(row['data']);path=ROOT/(d.get('raw_path') or '')
        if not path.is_file(): continue
        f=DB.execute('SELECT * FROM frontier WHERE url=?',(d['source_url'],)).fetchone()
        try:
            ext=extension(path.read_bytes()[:20000],d.get('content_type',''),'',d['final_url']) if 'sitemap' in d['source_url'] else d['format']
            if ext=='.xml':
                xml=etree.fromstring(path.read_bytes());locs=xml.xpath('//*[local-name()="loc"]/text()')
                for loc in locs:
                    norm=normalize(loc,d['final_url'])
                    if norm and (norm.endswith('/ewha/ewha.xml') or norm.endswith('/board/board.xml') or '/ewha/bachelor/' in norm or '/ewha/life/' in norm or '/ewha/academics/' in norm): enqueue(norm,d['final_url'],'sitemap entry',1,'sitemap',True)
                doc={'text':'\n'.join(locs),'parse_status':'discovery_only','entry_count':len(locs)}
            elif ext=='.html': doc=parse_html(path.read_bytes(),dict(f),d['final_url'])
            else: doc=extract(path,ext)
            d.update(doc);d['format']=ext
            sql('UPDATE documents SET data=? WHERE url=?',(jdump(d),d['source_url']))
            (ROOT/'03_정제문서'/'문서별'/(d['doc_id']+'.json')).write_text(jdump(d),encoding='utf-8')
        except Exception as exc: sql('INSERT OR IGNORE INTO review VALUES(?,?,?)',(d['source_url'],'reparse_error',str(exc)))
    # Retry incorrectly escaped public paths using canonical encoded URLs.
    for row in DB.execute('SELECT * FROM frontier WHERE status="failed"').fetchall():
        if normalize(row['url'])!=row['url']: enqueue(row['url'],row['parent'],row['label'],row['priority'],'canonical_path_retry',True)
    print('REPARSED',len(rows),flush=True)

def run(workers,reparse=False):
    init()
    if reparse: reparse_existing()
    running={};busy=set();last=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        while True:
            done=[f for f in running if f.done()]
            for f in done:
                item=running.pop(f);busy.discard(item['host'])
                try: result=f.result()
                except Exception as exc:
                    sql('UPDATE frontier SET status="failed",finished_at=? WHERE url=?',(now(),item['url']))
                    sql('INSERT OR IGNORE INTO review VALUES(?,?,?)',(item['url'],'worker_exception',repr(exc)))
                    print('ERROR',item['url'],str(exc),flush=True)
            with LOCK: pending=[dict(r) for r in DB.execute('SELECT * FROM (SELECT *, ROW_NUMBER() OVER(PARTITION BY host ORDER BY priority,created_at) AS host_rank FROM frontier WHERE status="pending") WHERE host_rank=1 ORDER BY priority,created_at')]
            for item in pending:
                if len(running)>=workers: break
                if item['host'] in busy: continue
                busy.add(item['host']);sql('UPDATE frontier SET status="running" WHERE url=?',(item['url'],))
                running[pool.submit(process,item)]=item
            if time.monotonic()-last>20:
                print(jdump(export()),flush=True);last=time.monotonic()
            if not pending and not running: break
            time.sleep(.2)
    print(jdump(export()),flush=True)

if __name__=='__main__':
    logging.getLogger('pypdf').setLevel(logging.ERROR)
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=12);ap.add_argument('--export',action='store_true');ap.add_argument('--reparse',action='store_true');args=ap.parse_args()
    if args.export: init();print(jdump(export()))
    else: run(args.workers,args.reparse)
