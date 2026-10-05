#!/bin/sh

# https://github.com/actions/runner/issues/3792 ;)
nap() { ping -c "${1:-2}" 127.0.0.1 >/dev/null 2>&1; }

trap 'ledkeytest ledoff; ledkeytest ledexit; echo; echo restored; exit 0' INT TERM

ledkeytest ledenter
while :; do
	ledkeytest ledon;  nap 2
	ledkeytest ledoff; nap 2
done
