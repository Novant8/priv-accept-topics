# Topics API analysis tools

This folder encloses the tools used to extract the information useful for analysing the Topics API usage.

## Domain extraction

`extract-domains.py` extracts a list of all the unique second-level domains contacted by the browser during the visit of a single website.

### Usage

```
extract-domains.py <PRIV_ACCEPT_OUTPUT>
```

* The *Priv-Accept* output refers to the complete JSON output with full network logs active.

### Output

It prints on `stdout` the unique domains extracted from *Priv-Accept*'s output, one per line.

## Domain attestation

`attest-domain.py` determines whether a given domain is *Attested*, by contacting the domain at the `https://<domain>/.well-known/privacy-sandbox-attestations.json` path and verifying whether it contains a valid attestation file for the Topics API.

### Usage

```
attest-domain.py [--timeout TIMEOUT] [--user_agent USER_AGENT] <DOMAIN>
```

* `--timeout TIMEOUT`: time the request client awaits for a page to load. 
* `--user_agent USER_AGENT`: user agent to be used by the request client.

### Output

Only if the given domain is *Attested*, the tool prints the domain and the relative attestation JSON on `stdout`, one per line in CSV notation. For example:
```
attested-domain1.com,"{""privacy_sandbox_attestations"": [...]}"
attested-domain2.com,"{""privacy_sandbox_attestations"": [...]}"
```
If the domain is not *Attested*, nothing is printed.

## Analyse Topics API

`analyze-topics-api.py` builds a more compact JSON file given *Priv-Accept*'s output and the list of *Allowed* and *Attested* sites found during the crawling.

### Usage

```
analyze-topics-api.py [-h] [--timeout TIMEOUT] [--attested_domains_file ATTESTED_DOMAINS_FILE]
                      [--allowed_domains_file ALLOWED_DOMAINS_FILE]
                      [--consent_managers_file CONSENT_MANAGERS_FILE] [--outfile OUTFILE]
                      [--pretty_print]
                      <INPUT_FILE>
```

* `--timeout TIMEOUT`: time the request client awaits for a page to load.
* `--attested_domains_file ATTESTED_DOMAINS_FILE`: path to the list of *Attested* domains.
* `--allowed_domains_file ALLOWED_DOMAINS_FILE`: path to the list of *Allowed* domains.
* `--consent_managers_file CONSENT_MANAGERS_FILE`: path to the list of consent manager domains.
* `--outfile OUTFILE`: path to where the final output should be produced.
* `--pretty-print`: if enabled, the output file will be beautified and printed in multiple lines, otherwise the output will be printed minified in a single line.

### Output

A JSON file containing the most important information for the Topics API analysis, such as:
* *(per-visit)* The collection of *Attested* and *Allowed* domains encountered.
* *(per-visit)* The collection of consent managers encountered.
* *(per-visit)* Whether Google Tag Manager (GTM) was found within the website during the visit.
* *(per-visit)* The collection of Topics API usages detected.
* Whether *Priv-Accept* has found and clicked a privacy banner.

For example:

```json
{
  "url": "https://website.com/",
  "first": {
    "attested_domains": [
        "domain.com",
        ...
    ],
    "allowed_domains": [...],
    "consent_managers": [...],
    "has_gtm": true,
    "topics_api_usages": [
        {
            "context_origin_url": "https://calling-party.com",
            "caller_source": "javascript",
            "usage_time": 123456
        }
    ]
  },
  "second": {
    ...
  },
  "banner_clicked": true
}
```
The `first` property refers to the *Before-Accept* visit, whereas `second` refers to the *After-Accept* visit.

## Get domain

`get_domain.py` is a small custom library that defines several functions to extract domain names of different levels from longer domains or full URLs.