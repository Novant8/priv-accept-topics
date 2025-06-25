# Privacy Sandbox analysis tools

This folder encloses the tools used to extract the information useful for analysing the Privacy Sandbox usage. For some tools it is necessary to have [**jq**](https://jqlang.org/) installed on your machine.

## 2LD domain extraction

`extract-domains.jq` extracts a list of all the unique second-level domains contacted by the browser during the visit of a single website.

### Usage

```
jq -L modules -f extract_contacted_2ld.jq
  --argjson visits <VISITS>
  <PRIV_ACCEPT_OUTPUT>
```

* The *Priv-Accept* output refers to the complete JSON output with full network logs active.
* The `visits` argument is a JSON array of strings, containing the list of visits to consider (e.g., `["first","second"]`).

### Output

It prints on `stdout` the unique domains extracted from *Priv-Accept*'s output, one per line.

## Domain attestation

`attest-domain.py` determines whether a given domain is *Attested*, by contacting the domain at the `https://<domain>/.well-known/privacy-sandbox-attestations.json` path and verifying whether it contains a valid attestation file for the Topics API.

### Usage

```
python attest-domain.py [--timeout TIMEOUT] [--user_agent USER_AGENT] <DOMAIN>
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

## Post process output

`post_process_output.jq` compacts *Priv-Accept*'s output into a single CSV line containing the data relevant for the analysis. It also extracts the list of *full* domains contacted during each visit into a `contacted_domains` field.

### Usage

```
jq -L modules -f extract_contacted_2ld.jq
  --argjson visits <VISITS>
  --argjson fields <FIELDS
  --arg position <POSITION>
  --arg full_net_log <0|1>
  <PRIV_ACCEPT_OUTPUT>
```

* The `visits` argument is a JSON array of strings containing the list of visits to consider, as specified in *Priv-Accept*'s output (e.g., `["first","second"]`).
* The `fields` argument is a JSON array of strings containing the list of arguments to consider for each visit, as specified in *Priv-Accept*'s output (e.g., `["api_calls","contacted_domains"]`).
* The `position` argument refers to the position of the website by popularity, according to the list used.
* If `full_net_log` is set to 1, it indicates that the crawler collected the full network logs (with the `--full_net_log` option enabled). 


### Output

A single CSV line per JSON file, with the following format:
```
position,website,{visit}_{field}
```
where `{visit}_{field}` is the combination of each visit with each field (e.g., `first_api_calls`, `first_contacted_domains`, etc.)

## Merge CSV

`merge-csv.py` merges two input CSV files into one, eventually adding a suffix of columns in common. The input files must have a header column, with at least one column in common to perform the *join* operation on.

### Usage

```
python merge-csv.py [-h]
  --join_on JOIN_ON [JOIN_ON ...]
  [--join_type {left,right,outer,inner,cross,left_anti,right_anti}] 
  [--suffix1 SUFFIX1] [--suffix2 SUFFIX2]
  [--sorted] [--output OUTPUT]
  file1 file2
```

* `file1` and `file2` are the paths to the two CSV files.
* `join_on` specifies which columns to perform the join on. This column must be present in both files.
* `join_type` specifies how the join is applied. Defaults to `inner`.
* `suffix1` and `suffix2` are appended to only those columns in common between `file1` and `file2` that are not included in `join_on`.
* If `sorted` is enabled, the output will be sorted by the `join_on` columns.
* `output` specifies the output file name. Defaults to `./merged.csv`.

## Get domain

`get_domain.jq` is a small JQ module that defines several functions to extract domain names of different levels from longer domains or full URLs.

# Docker container

All of these tools can be invoked from a pre-packaged [Docker container](https://hub.docker.com/r/salb98/priv-accept-post-process) as follows:
```
docker run [...docker_args] salb98/priv-accept-post-process
  <extract-contacted-2ld | attest-domain | post-process-output | merge-csv>
  [...tool_args]
```