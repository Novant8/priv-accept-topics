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
# - $csv_format: "boolean" (int 0 or 1) indicating whether to format the output into a single CSV line
######################################################################################################

include "get_domain";

.
| ($full_net_log | tonumber) as $full_net_log
| ($csv_format | tonumber) as $csv_format
| reduce $visits[] as $visit (.;
  # For each visit (if performed)...
  if .[$visit] != null then
    .[$visit] |= (
      . + {
        # DEFINE CONTACTED DOMAINS: extract all non-data domains that have been contacted during the visit
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
        ),
        # PARTITIONED COOKIES: extract all cookies with a partition key
        partitioned_cookies: (
          .cookies.cookies
          | map(select(.partitionKey != null))
        )
      }
    )
  else .
  end
)

| . as $output
| reduce $visits[] as $visit(
  {
    "position": $position | tonumber,
    "website": (
      if $full_net_log == 1 then
        .[$visits[0]].requests
          | map(.request.url)
      else
        .[$visits[0]].urls
      end
      | map(select(startswith("chrome://") | not))
      | first
    )
  };
  . + {
    ($visit): (
      if $output[$visit] != null then
        reduce $fields[] as $field (
          {};
          . + { ($field): $output[$visit]?[$field] }
        )
      else
        null
      end
    )
  }
)
| if $csv_format == 1 then
  # CSV OUTPUT: line with Tranco position + website URL + list of fields for each visit.
  [ .position, .website ]
  +
  [
    $visits[] as $visit
    | $fields[] as $field
    | .[$visit]?[$field]
    | if . == null then null else tostring end
  ]
  | @csv
else
  .
end
