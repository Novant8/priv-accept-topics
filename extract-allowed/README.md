# Extract *Allowed* domains

This folder contains tools and scripts for downloading and extracting the list of domains that are allowed to invoke the Privacy Sandbox APIs, according to Google.

The main script is `extract_allowed_domains.py`, which
1. downloads the list of Privacy Sandbox attestations using CUP (see [this repository](https://github.com/Novant8/chrome-component-downloader)),
2. extracts the `privacy-sandbox-attestations.dat` file,
3. retrieves the list of *Allowed* domains (and which APIs they can use) from the file.

## Requirements

To run the script, Python >3.9 is needed with the required packages (in `requirements.txt`) installed.

## Usage

```
extract_allowed_domains.py [-h] [--api_map API_MAP] [--output OUTPUT]
```

* `api_map` is a file that maps the internal ID of the API with its name. It can be found at `ps_api_map.json`.
* `output` is the name of the output file.

## Output

The script outputs a CSV file with the following structure:
```
domain,api1_allowed,api2_allowed,...
example.org,True,False,...
```

## Docker container

The *Allowed*-domain extraction script comes pre-packaged in a Docker container. It can be run through this command:

```
docker run [...docker_args]
    salb98/priv-accept-ps:2.0-beta
    [...crawler_args]
```

The outputs are placed inside the `/opt/priv-accept-ps/output` folder.