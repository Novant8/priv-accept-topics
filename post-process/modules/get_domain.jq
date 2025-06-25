def bad_domains:
  [
    "co.uk","co.jp","co.hu","co.il","com.au","co.ve",".co.in","com.ec","com.pk","co.th","co.nz","com.br","com.sg","com.sa",
    "com.do","co.za","com.hk","com.mx","com.ly","com.ua","com.eg","com.pe","com.tr","co.kr","com.ng","com.pe","com.pk","co.th",
    "com.au","com.ph","com.my","com.tw","com.ec","com.kw","co.in","co.id","com.com","com.vn","com.bd","com.ar",
    "com.co","com.vn","org.uk","net.gr","web.app"
  ];

def getFullDomain:
  capture("^(?:[a-zA-Z][a-zA-Z0-9+.-:]*://)?(?<domain>[^/?#]+)").domain?;

# Get the 3LD (third-level domain) from a URL
def get3LD:
  getFullDomain
  | if length == 0 then null
    else
      sub("\\.$"; "") 
      | split(".") as $names
      | ($names | length) as $len
      | ($names | .[($len - 3):]) as $tln_array
      | $tln_array | join(".")
    end;

def getGood2LD:
  getFullDomain as $fqdn
  | if ($fqdn | length) == 0 then null
    else
      ($fqdn | sub("\\.$"; "")) as $fqdn2
      | ($fqdn2 | split(".")) as $names
      | ($names | length) as $len
      | ($names | .[($len - 2):]) as $tln_array
      | ($tln_array | join(".")) as $tln
      | if bad_domains | index($tln) then
          get3LD
        else
          $tln
        end
    end;