#!/bin/bash
set -e

cd $(dirname $0)

[ -d "dist" ] || mkdir "dist"

shiv -c kaniko-build -o dist/kaniko-build .
