#!/bin/bash
# 依赖包检测与自动配置工具
# 功能：检测缺失的Python/Node.js包并安装，智能配置镜像源（仅中国IP使用国内镜像）
# name: 依赖包检测与管理
# cron: 30 4 * * *

# 定义目标镜像源
PYPI_TARGET_MIRROR="https://pypi.doubanio.com/simple/"  # PyPI豆瓣镜像
NPM_TARGET_MIRROR="https://registry.npmmirror.com/"     # npm淘宝镜像
PYPI_GLOBAL_MIRROR="https://pypi.org/simple/"           # PyPI官方源
NPM_GLOBAL_MIRROR="https://registry.npmjs.org/"         # npm官方源

# 定义检测时间范围（天数）
DETECTION_DAYS=3

# IP地址检查函数
check_ip_location() {
    echo "=== 检测IP地址位置 ==="
    
    # 定义多个IP检测服务，提高可靠性
    local ip_services=(
        "cip.cc"
        "ip.cn"
        "myip.ipip.net"
    )
    
    local ip_info=""
    local service_used=""
    
    # 依次尝试不同的IP检测服务
    for service in "${ip_services[@]}"; do
        echo "尝试使用 $service 检测IP位置..."
        
        case $service in
            "cip.cc")
                ip_info=$(timeout 8 curl -s http://cip.cc 2>/dev/null)
                ;;
            "ip.cn")
                ip_info=$(timeout 8 curl -s http://ip.cn 2>/dev/null)
                ;;
            "myip.ipip.net")
                ip_info=$(timeout 8 curl -s http://myip.ipip.net 2>/dev/null)
                ;;
        esac
        
        if [ $? -eq 0 ] && [ -n "$ip_info" ]; then
            service_used="$service"
            echo "✓ 成功从 $service 获取IP信息"
            break
        else
            echo "✗ $service 服务不可用"
            ip_info=""
        fi
    done
    
    # 如果所有服务都失败
    if [ -z "$ip_info" ]; then
        echo "⚠️  所有IP检测服务均不可用，将使用官方镜像源"
        echo "   建议：检查网络连接或手动配置镜像源"
        return 1
    fi
    
    echo -e "\nIP信息 (来源: $service_used)："
    echo "$ip_info"
    
    # 检查是否包含"中国"关键字
    if echo "$ip_info" | grep -iE "(中国|China|CN|beijing|shanghai|guangzhou|shenzhen)" >/dev/null; then
        echo -e "\n✓ 检测到中国IP地址，将使用国内镜像源加速"
        echo "   优势：显著提升包下载速度"
        return 0
    else
        echo -e "\n✓ 检测到海外IP地址，将使用官方镜像源"
        echo "   说明：保持使用原始官方源"
        return 1
    fi
}

# Python包名映射（日志包名 -> 实际安装包名）
declare -A PYTHON_PACKAGE_MAP=(
    ["execjs"]="PyExecJS"
    ["cv2"]="opencv-python"
    ["PIL"]="Pillow"
    ["sklearn"]="scikit-learn"
    ["yaml"]="PyYAML"
    ["bs4"]="beautifulsoup4"
    ["dateutil"]="python-dateutil"
)

# 镜像源检测与配置函数
configure_pypi_mirror() {
    echo -e "\n=== 配置PyPI镜像源 ==="
    
    # 根据IP位置选择镜像源
    local target_mirror
    local trusted_host=""
    
    if [ "$IS_CHINA_IP" = "true" ]; then
        target_mirror="$PYPI_TARGET_MIRROR"
        trusted_host="pypi.doubanio.com"
        echo "使用国内镜像源：$target_mirror"
    else
        target_mirror="$PYPI_GLOBAL_MIRROR"
        echo "使用官方镜像源：$target_mirror"
    fi
    
    current_pypi_mirror=$(pip3 config get global.index-url 2>/dev/null | grep -v '^#\|^$' | sed 's/[ \t]*$//')
    
    if [ -z "$current_pypi_mirror" ]; then
        echo "✗ 未设置PyPI镜像源，配置为：$target_mirror"
        pip3 config set global.index-url "$target_mirror"
        if [ -n "$trusted_host" ]; then
            pip3 config set global.trusted-host "$trusted_host"
        fi
        echo "✓ PyPI镜像源配置完成"
    elif [ "$current_pypi_mirror" != "$target_mirror" ]; then
        echo "✗ 当前PyPI镜像：$current_pypi_mirror"
        echo "→ 自动切换至目标镜像：$target_mirror"
        pip3 config set global.index-url "$target_mirror"
        if [ -n "$trusted_host" ]; then
            pip3 config set global.trusted-host "$trusted_host"
        fi
        echo "✓ 已自动切换至目标镜像"
    else
        echo "✓ 已使用目标PyPI镜像：$target_mirror"
    fi
}

configure_npm_mirror() {
    echo -e "\n=== 配置npm/pnpm镜像源 ==="
    
    # 根据IP位置选择镜像源
    local target_mirror
    
    if [ "$IS_CHINA_IP" = "true" ]; then
        target_mirror="$NPM_TARGET_MIRROR"
        echo "使用国内镜像源：$target_mirror"
    else
        target_mirror="$NPM_GLOBAL_MIRROR"
        echo "使用官方镜像源：$target_mirror"
    fi
    
    current_npm_mirror=$(npm config get registry 2>/dev/null | sed 's/[ \t]*$//')
    
    if [ -z "$current_npm_mirror" ] || [ "$current_npm_mirror" = "https://registry.npmjs.org/" ]; then
        echo "✗ 未设置或使用npm官方源，配置为：$target_mirror"
        npm config set registry "$target_mirror" >/dev/null 2>&1
        echo "✓ npm/pnpm镜像源配置完成"
    elif [ "$current_npm_mirror" != "$target_mirror" ]; then
        echo "✗ 当前npm镜像：$current_npm_mirror"
        echo "→ 自动切换至目标镜像：$target_mirror"
        npm config set registry "$target_mirror" >/dev/null 2>&1
        echo "✓ 已自动切换至目标镜像"
    else
        echo "✓ 已使用目标镜像：$target_mirror"
    fi
}

# 执行IP检查和镜像源配置
echo "=== 开始智能镜像源配置 ==="

# 检查IP位置并设置全局变量
if check_ip_location; then
    IS_CHINA_IP="true"
else
    IS_CHINA_IP="false"
fi

echo -e "\n=== 根据IP位置配置镜像源 ==="
configure_pypi_mirror
configure_npm_mirror

# 依赖包检测与安装
echo -e "\n=== 开始依赖包检测 ==="
echo "扫描近${DETECTION_DAYS}天的日志文件..."

# 临时文件设置
PYTHON_PACKAGES_FILE="/tmp/python_packages.txt"
NODEJS_PACKAGES_FILE="/tmp/nodejs_packages.txt"
> "$PYTHON_PACKAGES_FILE"
> "$NODEJS_PACKAGES_FILE"

# Python包检测
echo -e "\n=== Python包检测 ==="
echo "查找包含ModuleNotFoundError的日志："
find /ql -name '*.log' -type f -mtime -${DETECTION_DAYS} -exec grep -l 'ModuleNotFoundError\|No module named' {} \; 2>/dev/null

echo -e "\n提取缺失的Python包："
find /ql -name '*.log' -type f -mtime -${DETECTION_DAYS} -exec grep -h 'ModuleNotFoundError\|No module named' {} \; 2>/dev/null | \
sed -n "s/.*No module named '\([^']*\)'.*/\1/p; s/.*ModuleNotFoundError: No module named \([^ ]*\).*/\1/p" | \
sort | uniq | tee "$PYTHON_PACKAGES_FILE"

# Node.js包检测
echo -e "\n=== Node.js包检测 ==="
echo "查找包含模块错误的日志："
find /ql -name '*.log' -type f -mtime -${DETECTION_DAYS} -exec grep -l "Cannot find module\|MODULE_NOT_FOUND\|Error: Cannot resolve module" {} \; 2>/dev/null

echo -e "\n提取缺失的Node.js包："
find /ql -name '*.log' -type f -mtime -${DETECTION_DAYS} -exec grep -h "Cannot find module\|MODULE_NOT_FOUND\|Error: Cannot resolve module" {} \; 2>/dev/null | \
sed -n "s/.*Cannot find module '\([^']*\)'.*/\1/p; s/.*Cannot find module \"\([^\"]*\)\".*/\1/p; s/.*MODULE_NOT_FOUND.*'\([^']*\)'.*/\1/p; s/.*Error: Cannot resolve module '\([^']*\)'.*/\1/p" | \
grep -v "^/" | grep -v "^\." | \
sort | uniq | tee "$NODEJS_PACKAGES_FILE"

# 结果汇总
echo -e "\n=========================================="
echo "=== 检测结果汇总 ==="

# 显示Python包结果
if [ -s "$PYTHON_PACKAGES_FILE" ]; then
    echo -e "\n=== 缺失的Python包 ==="
    cat "$PYTHON_PACKAGES_FILE"
    
    echo -e "\nPython安装命令："
    echo -n "  pip3 install "
    tr '\n' ' ' < "$PYTHON_PACKAGES_FILE"
    echo
else 
    echo -e "\n✓ 未发现缺失的Python包"
fi

# 显示Node.js包结果
if [ -s "$NODEJS_PACKAGES_FILE" ]; then
    echo -e "\n=== 缺失的Node.js包 ==="
    cat "$NODEJS_PACKAGES_FILE"
    
    echo -e "\nnpm安装命令："
    echo -n "  npm install "
    tr '\n' ' ' < "$NODEJS_PACKAGES_FILE"
    echo -e "\n\npnpm安装命令（推荐）："
    echo -n "  pnpm install "
    tr '\n' ' ' < "$NODEJS_PACKAGES_FILE"
    echo
else
    echo -e "\n✓ 未发现缺失的Node.js包"
fi

# 安装缺失的包
if [ -s "$PYTHON_PACKAGES_FILE" ] || [ -s "$NODEJS_PACKAGES_FILE" ]; then
    echo -e "\n=========================================="
    echo "=== 开始安装缺失的包 ==="
    
    # 准备安装列表
    PYTHON_TO_INSTALL="/tmp/python_to_install.txt"
    NODEJS_TO_INSTALL="/tmp/nodejs_to_install.txt"
    > "$PYTHON_TO_INSTALL"
    > "$NODEJS_TO_INSTALL"
    
    # 验证Python包
    if [ -s "$PYTHON_PACKAGES_FILE" ]; then
        echo -e "\n检查Python包状态..."
        while IFS= read -r package; do
            if python3 -c "import $package" 2>/dev/null; then
                echo "✓ $package 已安装"
            else
                echo "✗ $package 需要安装"
                echo "$package" >> "$PYTHON_TO_INSTALL"
            fi
        done < "$PYTHON_PACKAGES_FILE"
    fi
    
    # 验证Node.js包
    if [ -s "$NODEJS_PACKAGES_FILE" ]; then
        echo -e "\n检查Node.js包状态..."
        while IFS= read -r package; do
            if node -e "require('$package')" 2>/dev/null; then
                echo "✓ $package 已安装"
            else
                echo "✗ $package 需要安装"
                echo "$package" >> "$NODEJS_TO_INSTALL"
            fi
        done < "$NODEJS_PACKAGES_FILE"
    fi
    
    # 安装Python包
    if [ -s "$PYTHON_TO_INSTALL" ]; then
        echo -e "\n安装Python包..."
        failed_packages=()
        success_count=0
        total_count=$(wc -l < "$PYTHON_TO_INSTALL")
        
        while IFS= read -r package; do
            # 检查是否需要映射包名
            install_package="$package"
            if [[ -n "${PYTHON_PACKAGE_MAP[$package]}" ]]; then
                install_package="${PYTHON_PACKAGE_MAP[$package]}"
                echo "📦 $package -> $install_package (使用映射包名)"
            fi
            
            echo "正在安装 $install_package..."
            if pip3 install "$install_package" >/dev/null 2>&1; then
                echo "✓ $install_package 安装成功"
                ((success_count++))
            else
                echo "✗ $install_package 安装失败"
                failed_packages+=("$package")
            fi
        done < "$PYTHON_TO_INSTALL"
        
        echo "📊 Python包安装统计: 成功 $success_count/$total_count"
        if [ ${#failed_packages[@]} -gt 0 ]; then
            echo "❌ 安装失败的包: ${failed_packages[*]}"
            echo "💡 建议手动检查这些包名或尝试其他安装方式"
        fi
    else
        echo -e "\n✓ 所有Python包已安装"
    fi
    
    # 安装Node.js包
    if [ -s "$NODEJS_TO_INSTALL" ]; then
        echo -e "\n安装Node.js包..."
        failed_js_packages=()
        js_success_count=0
        js_total_count=$(wc -l < "$NODEJS_TO_INSTALL")
        
        while IFS= read -r package; do
            echo "正在安装 $package..."
            if pnpm install "$package" >/dev/null 2>&1; then
                echo "✓ $package 安装成功"
                ((js_success_count++))
            else
                echo "✗ $package 安装失败"
                failed_js_packages+=("$package")
            fi
        done < "$NODEJS_TO_INSTALL"
        
        echo "📊 Node.js包安装统计: 成功 $js_success_count/$js_total_count"
        if [ ${#failed_js_packages[@]} -gt 0 ]; then
            echo "❌ 安装失败的包: ${failed_js_packages[*]}"
        fi
    else
        echo -e "\n✓ 所有Node.js包已安装"
    fi
    
    # 安装后验证
    echo -e "\n=== 安装后验证 ==="
    if [ -s "$PYTHON_TO_INSTALL" ]; then
        echo "验证Python包..."
        while IFS= read -r package; do
            if python3 -c "import $package" 2>/dev/null; then
                echo "✅ $package 验证通过"
            else
                echo "❌ $package 验证失败"
            fi
        done < "$PYTHON_TO_INSTALL"
    fi
    
    if [ -s "$NODEJS_TO_INSTALL" ]; then
        echo "验证Node.js包..."
        while IFS= read -r package; do
            if node -e "require('$package')" 2>/dev/null; then
                echo "✅ $package 验证通过"
            else
                echo "❌ $package 验证失败"
            fi
        done < "$NODEJS_TO_INSTALL"
    fi
    
    # 最终失败包汇总
    final_failed_python=()
    final_failed_nodejs=()
    
    if [ -s "$PYTHON_TO_INSTALL" ]; then
        while IFS= read -r package; do
            if ! python3 -c "import $package" 2>/dev/null; then
                final_failed_python+=("$package")
            fi
        done < "$PYTHON_TO_INSTALL"
    fi
    
    if [ -s "$NODEJS_TO_INSTALL" ]; then
        while IFS= read -r package; do
            if ! node -e "require('$package')" 2>/dev/null; then
                final_failed_nodejs+=("$package")
            fi
        done < "$NODEJS_TO_INSTALL"
    fi
    
    # 显示最终失败的包
    if [ ${#final_failed_python[@]} -gt 0 ] || [ ${#final_failed_nodejs[@]} -gt 0 ]; then
        echo -e "\n=========================================="
        echo "⚠️  最终安装失败的包汇总"
        echo "=========================================="
        
        if [ ${#final_failed_python[@]} -gt 0 ]; then
            echo -e "\n❌ Python包安装失败："
            for package in "${final_failed_python[@]}"; do
                echo "   • $package"
                # 检查是否有映射包名
                if [[ -n "${PYTHON_PACKAGE_MAP[$package]}" ]]; then
                    echo "     └─ 已尝试映射包名: ${PYTHON_PACKAGE_MAP[$package]}"
                fi
            done
            echo -e "\n💡 建议解决方案："
            echo "   1. 手动安装: pip3 install ${final_failed_python[*]}"
            echo "   2. 检查包名拼写是否正确"
            echo "   3. 尝试使用其他镜像源"
            echo "   4. 搜索替代包名"
        fi
        
        if [ ${#final_failed_nodejs[@]} -gt 0 ]; then
            echo -e "\n❌ Node.js包安装失败："
            for package in "${final_failed_nodejs[@]}"; do
                echo "   • $package"
            done
            echo -e "\n💡 建议解决方案："
            echo "   1. 手动安装: pnpm install ${final_failed_nodejs[*]}"
            echo "   2. 尝试npm安装: npm install ${final_failed_nodejs[*]}"
            echo "   3. 检查包名拼写是否正确"
            echo "   4. 搜索npm官网确认包名"
        fi
        
        echo -e "\n📝 注意事项："
        echo "   • 某些包可能需要特殊的安装条件或依赖"
        echo "   • 建议检查青龙面板日志获取更多错误信息"
        echo "   • 可以尝试在容器内手动安装测试"
    fi
    
    # 清理临时文件
    rm -f "$PYTHON_TO_INSTALL" "$NODEJS_TO_INSTALL"
    echo -e "\n=========================================="
    
    # 根据结果显示不同的完成消息
    if [ ${#final_failed_python[@]} -gt 0 ] || [ ${#final_failed_nodejs[@]} -gt 0 ]; then
        echo "⚠️  包安装完成（部分失败）"
    else
        echo "🎉 所有包安装成功"
    fi
else
    echo -e "\n🎉 没有缺失的包，系统依赖完整"
fi

# 清理所有临时文件
rm -f "$PYTHON_PACKAGES_FILE" "$NODEJS_PACKAGES_FILE"

echo -e "\n=========================================="
echo "=== 配置总结 ==="
echo "=========================================="

# 显示当前镜像源配置
echo -e "\n📋 当前镜像源配置："
current_pypi=$(pip3 config get global.index-url 2>/dev/null || echo "未设置")
current_npm=$(npm config get registry 2>/dev/null || echo "未设置")

echo "  • PyPI镜像源: $current_pypi"
echo "  • npm镜像源:  $current_npm"

# 显示IP检测结果
if [ "$IS_CHINA_IP" = "true" ]; then
    echo -e "\n🌏 IP位置: 中国境内"
    echo "  • 已自动配置国内镜像源加速"
    echo "  • 包下载速度将显著提升"
else
    echo -e "\n🌍 IP位置: 海外地区"
    echo "  • 已配置官方镜像源"
    echo "  • 如需使用国内镜像，可手动配置"
fi

echo -e "\n🔧 手动配置命令 (如需要)："
echo "  • 切换PyPI国内源: pip3 config set global.index-url https://pypi.doubanio.com/simple/"
echo "  • 切换PyPI官方源: pip3 config set global.index-url https://pypi.org/simple/"
echo "  • 切换npm国内源:  npm config set registry https://registry.npmmirror.com/"
echo "  • 切换npm官方源:  npm config set registry https://registry.npmjs.org/"

echo -e "\n=========================================="
echo "=== 所有操作完成 ==="
