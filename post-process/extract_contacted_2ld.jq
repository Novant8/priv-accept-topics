# Expects arguments:
# - visits: e.g., first, second,...
# - separate: "boolean" (int 0 or 1) indicating whether the URLs should be separated by visit
# - full_net_log: "boolean" (int 0 or 1) indicating whether the full network log is available

include "get_domain";

($full_net_log | tonumber) as $full_net_log
| ($separate | tonumber) as $separate
| . as $output
| reduce $visits[] as $visit (
    {};
    . + {
        ($visit): (
            if $full_net_log == 1 then
                $output[$visit]?.requests // []
                | map(.request.url)
            else
                $output[$visit]?.urls // []
            end
            | map(
                select(startswith("data:") | not)
                | getGood2LD
            )
            | unique
        )
    }
)
|
if $separate == 0 then
    flatten | unique[]
else
    .
end