#!/bin/bash
# 依赖包检测与自动配置工具
# 功能：检测缺失的Python/Node.js包并安装，自动配置国内镜像源
# name: 依赖包检测与管理
# cron: 30 4 * * *

# 定义目标镜像源
PYPI_TARGET_MIRROR="https://pypi.doubanio.com/simple/"  # PyPI豆瓣镜像
NPM_TARGET_MIRROR="https://registry.npmmirror.com/"     # npm淘宝镜像

# 定义检测时间范围（天数）
DETECTION_DAYS=3

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
    echo -e "\n=== 检测PyPI镜像源 ==="
    current_pypi_mirror=$(pip3 config get global.index-url 2>/dev/null | grep -v '^#\|^$' | sed 's/[ \t]*$//')
    
    if [ -z "$current_pypi_mirror" ]; then
        echo "✗ 未设置PyPI镜像源，配置为：$PYPI_TARGET_MIRROR"
        pip3 config set global.index-url "$PYPI_TARGET_MIRROR"
        pip3 config set global.trusted-host "pypi.doubanio.com"
        echo "✓ PyPI镜像源配置完成"
    elif [ "$current_pypi_mirror" != "$PYPI_TARGET_MIRROR" ]; then
        echo "✗ 当前PyPI镜像：$current_pypi_mirror"
        echo "→ 自动切换至目标镜像：$PYPI_TARGET_MIRROR"
        pip3 config set global.index-url "$PYPI_TARGET_MIRROR"
        pip3 config set global.trusted-host "pypi.doubanio.com"
        echo "✓ 已自动切换至目标镜像"
    else
        echo "✓ 已使用目标PyPI镜像：$PYPI_TARGET_MIRROR"
    fi
}

configure_npm_mirror() {
    echo -e "\n=== 检测npm/pnpm镜像源 ==="
    current_npm_mirror=$(npm config get registry 2>/dev/null | sed 's/[ \t]*$//')
    
    if [ -z "$current_npm_mirror" ] || [ "$current_npm_mirror" = "https://registry.npmjs.org/" ]; then
        echo "✗ 未设置或使用npm官方源，配置为：$NPM_TARGET_MIRROR"
        npm config set registry "$NPM_TARGET_MIRROR" >/dev/null 2>&1
        echo "✓ npm/pnpm镜像源配置完成"
    elif [ "$current_npm_mirror" != "$NPM_TARGET_MIRROR" ]; then
        echo "✗ 当前npm镜像：$current_npm_mirror"
        echo "→ 自动切换至目标镜像：$NPM_TARGET_MIRROR"
        npm config set registry "$NPM_TARGET_MIRROR" >/dev/null 2>&1
        echo "✓ 已自动切换至目标镜像"
    else
        echo "✓ 已使用目标npm镜像：$NPM_TARGET_MIRROR"
    fi
}

# 执行镜像源配置
echo "=== 开始镜像源检测与配置 ==="
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
echo "=== 所有操作完成 ==="
