#!/usr/bin/env bash
set -euo pipefail

battery-auditor collect --mode blackbox --name "blackbox-$(date +%Y%m%d-%H%M%S)"
