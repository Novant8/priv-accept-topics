######################################################################################################
# CRAWLER OUTPUT POST-PROCESSING
# This script extracts the most relevant information from the crawler's output relative to a single
# website. 
#
# Expects arguments:
# - $visits: e.g., first, second
# - $fields: e.g., contacted_domains, api_calls
# - $position: position number in Tranco list
# - $full_net_log: "boolean" (int 0 or 1) indicating whether the full network log is available
######################################################################################################

include "get_domain";

.
|
($full_net_log | tonumber) as $full_net_log
|
reduce $visits[] as $visit (.;
  # DEFINE CONTACTED DOMAINS: extract all non-data domains that have been contacted during the visit
  if .[$visit] != null then
    .[$visit] |= (
      . + {
        contacted_domains: (
          if $full_net_log == 1 then
            .requests
            | map(.request.url)
          else
            .urls
          end
          | map(
            select(startswith("data:") | not)
            | getFullDomain
          )
          | unique
        )
      }
    )
  else .
  end
)
|
# FINAL OUTPUT: CSV line with Tranco position + website URL + list of fields for each visit.
[
  ($position | tonumber),
  if $full_net_log == 1 then
    .[$visits[0]].requests
      | map(select(.request.url | startswith("chrome://") | not))
      | first
      | .request.url
  else
    .[$visits[0]].urls
      | map(select(startswith("chrome://") | not))
      | first
  end
]
+
[
  $visits[] as $visit
  | $fields[] as $field
  | .[$visit]?[$field]
  | if . == null then null else tostring end
]
| @csv