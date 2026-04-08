param(
    [Parameter(Mandatory = $true)]
    [string]$ImageTag
)

$ErrorActionPreference = "Stop"

Write-Host "Updating deployment to image tag: $ImageTag"
kubectl set image deployment/todo-deployment todo-backend=todo-backend:$ImageTag

Write-Host "Waiting for rollout to complete..."
try {
    kubectl rollout status deployment/todo-deployment --timeout=120s
    Write-Host "Rollout succeeded."
}
catch {
    Write-Host "Rollout failed. Undoing to previous revision..."
    kubectl rollout undo deployment/todo-deployment
    throw
}
