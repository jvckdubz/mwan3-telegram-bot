#!/bin/sh

URL="http://127.0.0.1:8081"
EVENT=$1

case "$EVENT" in
    to_reserve)
        iface="$2"
        curl -s -X POST -H "Content-Type: application/json" -d "{\"type\":\"to_reserve\",\"interface\":\"$iface\"}" "$URL"
        ;;
    to_main)
        curl -s -X POST -H "Content-Type: application/json" -d '{"type":"to_main"}' "$URL"
        ;;
esac
