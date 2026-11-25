# Run from PowerShell. Docker Desktop must run Linux containers.
param([string]$Docker = 'docker')
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
& $Docker build -f (Join-Path $PSScriptRoot 'Dockerfile') -t k5-day14-linux-checker $repoRoot
if ($LASTEXITCODE -ne 0) { throw 'Checker image build failed' }
# Host networking lets the unchanged checker contact containers it publishes
# through the mounted Docker daemon. The checker itself starts local Redis.
& $Docker run --rm --network host --mount "type=bind,source=$repoRoot,target=/workspace" --mount 'type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock' -e PYTHONIOENCODING=utf-8 --entrypoint bash k5-day14-linux-checker -o pipefail -c 'python check_production_ready.py 2>&1 | tee /workspace/reports/production_linux.txt'
exit $LASTEXITCODE
