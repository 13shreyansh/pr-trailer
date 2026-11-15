"""Readable, escaped code-context evidence behind an explicit review link."""
import html
from urllib.parse import quote

def code_context_page(row,report):
    context=report.get('codeContext',{})
    title=html.escape(row['title']);head=html.escape(report.get('headSha','')[:12])
    repo=row['repo'];items=[]
    for symbol in context.get('symbols',[]):
        href='https://github.com/'+quote(repo,safe='/')+'/blob/'+quote(report['headSha'])+'/'+quote(symbol['path'],safe='/')+'#L'+str(symbol['line'])
        items.append('<li><a href="'+html.escape(href,quote=True)+'" rel="noopener">'+html.escape(symbol['path'])+' · '+html.escape(symbol['name'])+'</a><p>'+html.escape(', '.join(symbol.get('relations',[])).replace('graph:',''))+'</p></li>')
    body='<ul>'+''.join(items)+'</ul>' if items else '<p>No code context is available for this run. The recorded tests still apply.</p>'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Code context · PR Trailer</title><link rel="stylesheet" href="/style.css"></head><body><main class="ledger"><nav><a href="/workspace">Back to workspace</a></nav><h1>'+title+'</h1><p>Code context from Entire Graph · head '+head+'</p><p>Symbols related to the requested change. Open a source line to inspect it in the measured revision.</p>'+body+'<p>Static relationships help review. An absent relationship does not prove a function is unused. Tests and the named human still decide what to merge.</p></main></body></html>').encode()
