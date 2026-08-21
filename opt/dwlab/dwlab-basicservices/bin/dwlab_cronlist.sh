#!/bin/bash
echo "=== System crontab ==="
cat /etc/crontab 2>/dev/null || echo "No system crontab"

echo -e "\n=== /etc/cron.d ==="
grep -H "" /etc/cron.d/* 2>/dev/null || echo "No files in /etc/cron.d"

echo -e "\n=== Cron job directories ==="
for dir in /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly; do
    [ -d "$dir" ] && echo "-- $dir --" && ls -1 "$dir"
done

echo -e "\n=== User crontabs ==="
for user in $(cut -f1 -d: /etc/passwd); do
    f="/var/spool/cron/crontabs/$user"
    [ -f "$f" ] && echo "-- $user --" && cat "$f"
done
