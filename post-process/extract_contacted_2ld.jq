# Expects arguments:
# - visits: e.g., first, second,...

include "get_domain";

[
    $visits[] as $visit
    | .[$visit]?.requests // []
    | .[]
    | .request.url
    | select(startswith("data:") | not)
    | getGood2LD
]
| unique | .[]