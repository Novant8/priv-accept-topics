# Privacy Sandbox Crawler Outputs

This folder contains a list of outputs relative to the Privacy Sandbox usage crawler. Each zip in this folder corresponds to a crawl performed on a certain date.

The naming scheme of the zip files is `outputs-YYYYMMDD.zip` where `YYYYMMDD` is the date when the crawling started.

## Zip contents

Each zip file contains the following files:
- [`allowed_domains.csv`](#allowed_domainscsv): Contains a list of **full** domains that are allowed to use certain Privacy Sandbox APIs, according to the attestation list saved in the browser's local configuration folder at the date of the crawling.

- [`attested_domains.csv`](#attested_domainscsv-and-allowed_attestedcsv): Contains a list of **full** domains that have been **contacted** during the crawling and contain an attestation file found at the `.well-known/...` path.

- [`allowed_attested.csv`](#attested_domainscsv-and-allowed_attestedcsv): Contains a list of **full** domains that are contained in `allowed_domains.csv` and contain contain an attestation file found at the `.well-known/...` path.

- [`crawler_output.csv`](#crawler_outputcsv): Main results file, contains the list of contacted domains, api calls and partitioned cookies recorded during the crawl, separated by visit, for each website.

### `allowed_domains.csv`

- Each row of this file corresponds to a website contained in the *Allowed* dataset.
- Columns:
    | Column    | Description |
    | ---       | --- |
    | domain    | The domain name
    | `topics_allowed`<br>`protected_audience_allowed`<br>`private_aggregation_allowed`<br>`attribution_reporting_allowed`<br>`shared_storage_allowed`<br>`fenced_storage_read_allowed` | Boolean value. If `true`, that website is allowed to use the correspondent API.

### `attested_domains.csv` and `allowed_attested.csv`

- Each row corresponds to an *Attested* website.
- Columns:
    | Column                | Description |
    | ---                   | --- |
    | domain                | The domain name
    | attestation_result    | Contents of the attestation file, as downloaded directly from the `.well-known/...` path.

### `crawler_output.csv`

Each row of this file corresponds to one website present in the Tranco List. Each websites contains the following information:

- List of **contacted domains** in their **full** form, represented as a JSON array of strings.

- List of **API calls** recorded, separated by API type. The strucutre of these calls is better explained in [this section](#api-calls-object).

- List of **partitioned cookies**. The data for each cookie is described in CDP's [Cookie](https://chromedevtools.github.io/devtools-protocol/tot/Network/#type-Cookie) type. All partitioned cookies have the `partitionKey` property set.

This information is present for each **visit**:
- **First-Accept**: before clicking the "Accept"/"Deny" button (*Accept* crawl).
- **Second-Accept**: after clicking the "Accept" button.
- **First-Deny**: before clicking the "Accept"/"Deny" button (*Deny* crawl).
- **Second-Deny**: after clicking the "Deny" button.

A summary of all column names can be found in [this section](#column-summary).

Notes:
- The information related to the **first** visit should be available for all websites. This information can be included in either *First-Accept*, *First-Deny*, or both.

- Some websites do not contain an "Accept"/"Deny" button that the crawler could find, or the crawler failed to load the website for a second time. In these cases, the data related to the failed visit is set to a `null` value.

#### API calls object

API calls are encoded as a JSON object with the following structure:
```json
{
    "<api>": {
        "javascript_functions": [...],
        "cdp_events": [...],
        "db_data": [...]
    }
}
```
- `<api>` can be:
    - `topics`
    - `protected_audience`
    - `private_state_tokens`
    - `attribution_reporting`
    - `related_website_sets`
    - `shared_storage`
    - `fenced_frames`
    - `fedcm`
- `private_aggregation`

- `javascript_functions` is a list of API invocations through a JavaScript function. They have the following structure:
    ```json
        {
            "description": "...",
            "accessType": "call",
            "args": {
                "0": {...},
                "1": {...},
                ...
            },
            "retVal": ...,
            "source": "...",
            "frameUrl": "..."
        }
    ```
    - `description` is the name of the function.
    - `args` is the list of arguments passed to the function, in order.
    - `retVal` is the return value.
    - `source` and `frameUrl` are the URLs of the script and the page/iframe which contains it, respectively.

- `cdp_events` is a list of API invocations as detected from using the CDP protocol. The structure is the following:
    ```json
    {
        "cdp_event_name": "...",
        ...
    }
    ```
    The rest of the payload depends on the type of event. Consult the [DevTools Protocol documentation](https://chromedevtools.github.io/devtools-protocol/) for more information.

- `db_data` is a list of API invocations extracted from a local database. For now, it is only available for the Topics and Private Aggregation API.

#### Column summary

| Column                                    | Notes |
| ---                                       | --- |
| `website`                                 | Not null, contains the website's origin (`http[s]://<website>/`).
| `first_contacted_domains_accept`          | Nullable, JSON array. If null, the visit has failed.
| `first_api_calls_accept`                  | Nullable, JSON object. If null, the visit has failed.
| `first_partitioned_cookies_accept`        | Nullable, JSON object. If null, the visit has failed.
| `first_contacted_domains_deny`            | Nullable, JSON array. If null, the visit has failed.
| `first_api_calls_deny`                    | Nullable, JSON object. If null, the visit has failed.
| `first_partitioned_cookies_deny`          | Nullable, JSON object. If null, the visit has failed.
| `second_contacted_domains_accept`         | Nullable, JSON array. If this field is null and the `first_*_accept` fields are not null, the crawler has failed to find an "Accept" button.
| `second_api_calls_accept`                 | Nullable, JSON object. If this field is null and the `first_*_accept` fields are not null, the crawler has failed to find an "Accept" button.
| `second_partitioned_cookies_accept`         | Nullable, JSON object. If this field is null and the `first_*_accept` fields are not null, the crawler has failed to find a "Deny" button.
| `second_contacted_domains_deny`           | Nullable, JSON array. If this field is null and the `first_*_deny` fields are not null, the crawler has failed to find a "Deny" button.
| `second_api_calls_deny`                   | Nullable, JSON object. If this field is null and the `first_*_deny` fields are not null, the crawler has failed to find a "Deny" button.
| `second_partitioned_cookies_deny`         | Nullable, JSON object. If this field is null and the `first_*_deny` fields are not null, the crawler has failed to find a "Deny" button.
