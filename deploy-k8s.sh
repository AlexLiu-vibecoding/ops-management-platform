#!/bin/bash
# ============================================================
# OpsCenter - Kubernetes 部署脚本
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
NAMESPACE="opscenter"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/k8s"
HELM_DIR="${SCRIPT_DIR}/helm/opscenter"

# 函数定义
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."

    # 检查 kubectl
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl 未安装，请先安装 kubectl"
        exit 1
    fi
    print_success "kubectl 已安装: $(kubectl version --client --short 2>/dev/null || echo 'unknown')"

    # 检查集群连接
    if ! kubectl cluster-info &> /dev/null; then
        print_error "无法连接到 Kubernetes 集群"
        exit 1
    fi
    print_success "Kubernetes 集群连接正常"

    # 检查 Helm（可选）
    if command -v helm &> /dev/null; then
        print_success "Helm 已安装: $(helm version --short 2>/dev/null || echo 'unknown')"
        HELM_AVAILABLE=true
    else
        print_warning "Helm 未安装，将使用 YAML 清单部署"
        HELM_AVAILABLE=false
    fi
}

# 检查命名空间
check_namespace() {
    print_info "检查命名空间 ${NAMESPACE}..."

    if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
        print_warning "命名空间 ${NAMESPACE} 不存在，将自动创建"
    else
        print_success "命名空间 ${NAMESPACE} 已存在"
    fi
}

# 生成 TLS 证书（可选）
generate_tls_cert() {
    local use_tls=${1:-false}

    if [ "$use_tls" = true ]; then
        print_info "生成 TLS 证书..."

        if kubectl get secret opscenter-tls-secret -n ${NAMESPACE} &> /dev/null; then
            print_warning "TLS Secret 已存在，跳过生成"
            return 0
        fi

        read -p "请输入域名 (默认: opscenter.example.com): " DOMAIN
        DOMAIN=${DOMAIN:-opscenter.example.com}

        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /tmp/tls.key \
            -out /tmp/tls.crt \
            -subj "/CN=${DOMAIN}" 2>/dev/null

        kubectl create secret tls opscenter-tls-secret \
            --cert=/tmp/tls.crt \
            --key=/tmp/tls.key \
            -n ${NAMESPACE}

        rm -f /tmp/tls.key /tmp/tls.crt
        print_success "TLS Secret 已创建"
    fi
}

# 使用 YAML 清单部署
deploy_with_yaml() {
    print_info "使用 YAML 清单部署..."

    # 按顺序部署
    local files=(
        "00-namespace.yaml"
        "01-configmap.yaml"
        "02-secret.yaml"
        "09-rbac.yaml"
        "03-backend-deployment.yaml"
        "04-backend-service.yaml"
        "05-frontend-deployment.yaml"
        "06-frontend-service.yaml"
    )

    for file in "${files[@]}"; do
        local filepath="${K8S_DIR}/${file}"
        if [ -f "$filepath" ]; then
            print_info "应用 ${file}..."
            kubectl apply -f "$filepath"
            print_success "应用 ${file} 完成"
        else
            print_warning "文件 ${file} 不存在，跳过"
        fi
    done

    print_success "YAML 清单部署完成"
}

# 使用 Helm Chart 部署
deploy_with_helm() {
    if [ "$HELM_AVAILABLE" = false ]; then
        print_error "Helm 不可用，请使用 YAML 清单部署"
        exit 1
    fi

    print_info "使用 Helm Chart 部署..."

    # 检查 Helm Chart 是否存在
    if [ ! -f "${HELM_DIR}/Chart.yaml" ]; then
        print_error "Helm Chart 不存在: ${HELM_DIR}"
        exit 1
    fi

    # 检查是否已安装
    if helm list -n ${NAMESPACE} | grep -q "opscenter"; then
        print_warning "Helm Release 已存在，执行升级..."
        helm upgrade opscenter "${HELM_DIR}" \
            --namespace ${NAMESPACE} \
            --values "${HELM_DIR}/values.yaml"
    else
        print_info "安装 Helm Release..."
        helm install opscenter "${HELM_DIR}" \
            --namespace ${NAMESPACE} \
            --create-namespace \
            --values "${HELM_DIR}/values.yaml"
    fi

    print_success "Helm Chart 部署完成"
}

# 等待 Pod 就绪
wait_for_pods() {
    print_info "等待 Pod 就绪..."

    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        local not_ready=$(kubectl get pods -n ${NAMESPACE} --no-headers | grep -v Running | grep -v Completed | wc -l)

        if [ $not_ready -eq 0 ]; then
            print_success "所有 Pod 已就绪"
            kubectl get pods -n ${NAMESPACE}
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 5
    done

    print_error "Pod 启动超时"
    kubectl get pods -n ${NAMESPACE}
    return 1
}

# 显示部署信息
show_deployment_info() {
    print_info "显示部署信息..."

    echo ""
    echo "================================"
    echo "部署信息"
    echo "================================"
    echo ""

    # Pod 状态
    echo "Pod 状态:"
    kubectl get pods -n ${NAMESPACE}
    echo ""

    # Service 状态
    echo "Service 状态:"
    kubectl get svc -n ${NAMESPACE}
    echo ""

    # Ingress 状态
    if kubectl get ingress -n ${NAMESPACE} &> /dev/null; then
        echo "Ingress 状态:"
        kubectl get ingress -n ${NAMESPACE}
        echo ""

        # 显示访问地址
        local ingress_host=$(kubectl get ingress opscenter-ingress -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)
        if [ -n "$ingress_host" ]; then
            echo "访问地址: https://${ingress_host}"
        fi
    fi

    echo ""
    echo "================================"
    echo "常用命令"
    echo "================================"
    echo ""
    echo "查看后端日志:"
    echo "  kubectl logs -f deployment/opscenter-backend -n ${NAMESPACE}"
    echo ""
    echo "查看前端日志:"
    echo "  kubectl logs -f deployment/opscenter-frontend -n ${NAMESPACE}"
    echo ""
    echo "端口转发:"
    echo "  kubectl port-forward svc/opscenter-frontend-service 8080:80 -n ${NAMESPACE}"
    echo "  然后访问: http://localhost:8080"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "================================"
    echo "OpsCenter - Kubernetes 部署"
    echo "================================"
    echo ""

    # 检查依赖
    check_dependencies
    echo ""

    # 检查命名空间
    check_namespace
    echo ""

    # 询问部署方式
    echo "请选择部署方式:"
    echo "1) 使用 YAML 清单部署（推荐）"
    echo "2) 使用 Helm Chart 部署"
    read -p "请输入选择 (1/2): " deploy_choice

    # 是否生成 TLS 证书
    read -p "是否生成 TLS 证书? (y/n): " generate_tls
    generate_tls_cert=false
    if [ "$generate_tls" = "y" ] || [ "$generate_tls" = "Y" ]; then
        generate_tls_cert=true
    fi
    echo ""

    # 执行部署
    if [ "$deploy_choice" = "2" ]; then
        deploy_with_helm
    else
        deploy_with_yaml
    fi
    echo ""

    # 等待 Pod 就绪
    read -p "是否等待 Pod 就绪? (y/n): " wait_pods
    if [ "$wait_pods" = "y" ] || [ "$wait_pods" = "Y" ]; then
        wait_for_pods
    fi
    echo ""

    # 显示部署信息
    show_deployment_info

    print_success "部署完成！"
}

# 执行主函数
main "$@"
