from urllib.parse import urlparse

bad_domains=set("co.uk co.jp co.hu co.il com.au co.ve .co.in com.ec com.pk co.th co.nz com.br com.sg com.sa \
com.do co.za com.hk com.mx com.ly com.ua com.eg com.pe com.tr co.kr com.ng com.pe com.pk co.th \
com.au com.ph com.my com.tw com.ec com.kw co.in co.id com.com com.vn com.bd com.ar \
com.co com.vn org.uk net.gr web.app".split())

def getGood2LD(url):
    fqdn = getFullDomain(url)
    if len(fqdn) == 0:
        return None
    if fqdn[-1] == ".":
        fqdn = fqdn[:-1]    
    names = fqdn.split(".")
    if ".".join(names[-2:]) in bad_domains:
        return get3LD(fqdn)
    tln_array = names[-2:]
    tln = ""
    for s in tln_array:
        tln = tln + "." + s
    return tln[1:]

def get3LD(url):
    fqdn = getFullDomain(url)
    if len(fqdn) == 0:
        return None
    if fqdn[-1] == ".":
        fqdn = fqdn[:-1]
    names = fqdn.split(".")
    tln_array = names[-3:]
    tln = ""
    for s in tln_array:
        tln = tln + "." + s
    return tln[1:]

def getFullDomain(url) -> str:
    parse_result = urlparse(url)
    domain = parse_result.netloc if len(parse_result.scheme) > 0 else parse_result.path
    domain_levels = domain.strip(".").split(".")
    level = len(domain_levels)
    return '.'.join(domain_levels[-level:])