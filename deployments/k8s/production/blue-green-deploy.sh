#!/bin/bash
# deployments/k8s/production/blue-green-deploy.sh
# Blue-Green Deployment Script for Production

set -euo pipefail

# Configuration
NAMESPACE="video-summarizer-prod"
IMAGE_TAG="${1:-latest}"
REGISTRY="ghcr.io/yourorg/video-summarizer"
TIMEOUT="600s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    # Check if current context is correct
    CURRENT_CONTEXT=$(kubectl config current-context)
    log_info "Current kubectl context: $CURRENT_CONTEXT"
    
    # Verify cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Get current deployment color
get_current_color() {
    # Check which color is currently active based on service selector
    local current_selector=$(kubectl get service backend-service -n "$NAMESPACE" -o jsonpath='{.spec.selector.color}' 2>/dev/null || echo "")
    
    if [[ "$current_selector" == "blue" ]]; then
        echo "blue"
    elif [[ "$current_selector" == "green" ]]; then
        echo "green"
    else
        # Default to blue if no color is set
        echo "blue"
    fi
}

# Deploy to inactive environment
deploy_inactive_environment() {
    local current_color="$1"
    local new_color="$2"
    
    log_info "Deploying to $new_color environment with image tag: $IMAGE_TAG"
    
    # Update deployment with new image and color
    kubectl patch deployment backend-deployment -n "$NAMESPACE" -p \
        "{\"spec\":{\"template\":{\"metadata\":{\"labels\":{\"color\":\"$new_color\"}},\"spec\":{\"containers\":[{\"name\":\"backend\",\"image\":\"$REGISTRY-backend:$IMAGE_TAG\"}]}}}}"
    
    kubectl patch deployment worker-deployment -n "$NAMESPACE" -p \
        "{\"spec\":{\"template\":{\"metadata\":{\"labels\":{\"color\":\"$new_color\"}},\"spec\":{\"containers\":[{\"name\":\"worker\",\"image\":\"$REGISTRY-worker:$IMAGE_TAG\"}]}}}}"
    
    kubectl patch deployment frontend-deployment -n "$NAMESPACE" -p \
        "{\"spec\":{\"template\":{\"metadata\":{\"labels\":{\"color\":\"$new_color\"}},\"spec\":{\"containers\":[{\"name\":\"frontend\",\"image\":\"$REGISTRY-frontend:$IMAGE_TAG\"}]}}}}"
    
    # Wait for rollout to complete
    log_info "Waiting for $new_color deployment to be ready..."
    kubectl rollout status deployment/backend-deployment -n "$NAMESPACE" --timeout="$TIMEOUT"
    kubectl rollout status deployment/worker-deployment -n "$NAMESPACE" --timeout="$TIMEOUT"
    kubectl rollout status deployment/frontend-deployment -n "$NAMESPACE" --timeout="$TIMEOUT"
    
    log_success "$new_color environment deployed successfully"
}

# Run health checks
run_health_checks() {
    local color="$1"
    
    log_info "Running health checks for $color environment..."
    
    # Get pod IPs for the new color
    local backend_pods=$(kubectl get pods -n "$NAMESPACE" -l app=backend,color="$color" -o jsonpath='{.items[*].status.podIP}')
    
    if [[ -z "$backend_pods" ]]; then
        log_error "No backend pods found for color $color"
        return 1
    fi
    
    # Test each backend pod
    for pod_ip in $backend_pods; do
        log_info "Testing backend pod at $pod_ip..."
        
        # Health check
        if ! kubectl run --rm -i --restart=Never --image=curlimages/curl:latest curl-test-$(date +%s) -- \
            curl -f --max-time 10 "http://$pod_ip:8000/health" &> /dev/null; then
            log_error "Health check failed for pod $pod_ip"
            return 1
        fi
        
        # Metrics check
        if ! kubectl run --rm -i --restart=Never --image=curlimages/curl:latest curl-test-$(date +%s) -- \
            curl -f --max-time 10 "http://$pod_ip:8000/metrics" &> /dev/null; then
            log_warning "Metrics endpoint check failed for pod $pod_ip"
        fi
    done
    
    log_success "Health checks passed for $color environment"
}

# Switch traffic to new environment
switch_traffic() {
    local new_color="$1"
    
    log_info "Switching traffic to $new_color environment..."
    
    # Update service selectors to point to new color
    kubectl patch service backend-service -n "$NAMESPACE" -p \
        "{\"spec\":{\"selector\":{\"color\":\"$new_color\"}}}"
    
    kubectl patch service frontend-service -n "$NAMESPACE" -p \
        "{\"spec\":{\"selector\":{\"color\":\"$new_color\"}}}"
    
    # Note: Worker service doesn't need traffic switching as it's queue-based
    
    log_success "Traffic switched to $new_color environment"
}

# Cleanup old environment
cleanup_old_environment() {
    local old_color="$1"
    
    log_info "Cleaning up $old_color environment..."
    
    # Scale down old deployments
    kubectl scale deployment backend-deployment -n "$NAMESPACE" --replicas=0 --selector="color=$old_color"
    kubectl scale deployment frontend-deployment -n "$NAMESPACE" --replicas=0 --selector="color=$old_color"
    
    # Keep worker running for a bit to finish processing tasks
    sleep 30
    kubectl scale deployment worker-deployment -n "$NAMESPACE" --replicas=0 --selector="color=$old_color"
    
    log_success "Old $old_color environment cleaned up"
}

# Rollback function
rollback() {
    local current_color="$1"
    local previous_color="$2"
    
    log_warning "Rolling back to $previous_color environment..."
    
    # Switch traffic back
    kubectl patch service backend-service -n "$NAMESPACE" -p \
        "{\"spec\":{\"selector\":{\"color\":\"$previous_color\"}}}"
    
    kubectl patch service frontend-service -n "$NAMESPACE" -p \
        "{\"spec\":{\"selector\":{\"color\":\"$previous_color\"}}}"
    
    # Scale up previous environment if needed
    kubectl scale deployment backend-deployment -n "$NAMESPACE" --replicas=3 --selector="color=$previous_color"
    kubectl scale deployment frontend-deployment -n "$NAMESPACE" --replicas=2 --selector="color=$previous_color"
    kubectl scale deployment worker-deployment -n "$NAMESPACE" --replicas=2 --selector="color=$previous_color"
    
    log_success "Rollback completed"
}

# Main deployment function
main() {
    log_info "Starting Blue-Green deployment for Video Summarizer"
    log_info "Image tag: $IMAGE_TAG"
    
    # Check prerequisites
    check_prerequisites
    
    # Determine current and new colors
    CURRENT_COLOR=$(get_current_color)
    if [[ "$CURRENT_COLOR" == "blue" ]]; then
        NEW_COLOR="green"
    else
        NEW_COLOR="blue"
    fi
    
    log_info "Current active environment: $CURRENT_COLOR"
    log_info "Deploying to: $NEW_COLOR"
    
    # Deploy to inactive environment
    deploy_inactive_environment "$CURRENT_COLOR" "$NEW_COLOR"
    
    # Run health checks
    if ! run_health_checks "$NEW_COLOR"; then
        log_error "Health checks failed, aborting deployment"
        exit 1
    fi
    
    # Switch traffic
    switch_traffic "$NEW_COLOR"
    
    # Wait a bit and run final verification
    log_info "Waiting 30 seconds before final verification..."
    sleep 30
    
    # Final health check through the service
    log_info "Running final health check through load balancer..."
    if ! kubectl run --rm -i --restart=Never --image=curlimages/curl:latest curl-final-$(date +%s) -- \
        curl -f --max-time 10 "http://backend-service.$NAMESPACE.svc.cluster.local:8000/health" &> /dev/null; then
        log_error "Final health check failed, rolling back..."
        rollback "$NEW_COLOR" "$CURRENT_COLOR"
        exit 1
    fi
    
    log_success "Final health check passed"
    
    # Cleanup old environment
    cleanup_old_environment "$CURRENT_COLOR"
    
    log_success "Blue-Green deployment completed successfully!"
    log_info "Active environment is now: $NEW_COLOR"
    
    # Display deployment info
    echo ""
    log_info "Deployment Summary:"
    echo "  - Image Tag: $IMAGE_TAG"
    echo "  - Active Color: $NEW_COLOR"
    echo "  - Namespace: $NAMESPACE"
    echo "  - Deployment Time: $(date)"
    echo ""
    
    # Show pod status
    log_info "Current pod status:"
    kubectl get pods -n "$NAMESPACE" -o wide
}

# Error handling
trap 'log_error "Deployment failed at line $LINENO"' ERR

# Run main function
main "$@"