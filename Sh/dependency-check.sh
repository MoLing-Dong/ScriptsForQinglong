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
        npm config set registry "$NPM_TARGET_MIRROR"
        echo "✓ npm/pnpm镜像源配置完成"
    elif [ "$current_npm_mirror" != "$NPM_TARGET_MIRROR" ]; then
        echo "✗ 当前npm镜像：$current_npm_mirror"
        echo "→ 自动切换至目标镜像：$NPM_TARGET_MIRROR"
        npm config set registry "$NPM_TARGET_MIRROR"
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
        pip3 install $(cat "$PYTHON_TO_INSTALL" | tr '\n' ' ')
        echo "✓ Python包安装完成"
    else
        echo -e "\n✓ 所有Python包已安装"
    fi
    
    # 安装Node.js包
    if [ -s "$NODEJS_TO_INSTALL" ]; then
        echo -e "\n安装Node.js包..."
        while IFS= read -r package; do
            echo "安装 $package..."
            pnpm install "$package"
        done < "$NODEJS_TO_INSTALL"
        echo "✓ Node.js包安装完成"
    else
        echo -e "\n✓ 所有Node.js包已安装"
    fi
    
    # 清理临时文件
    rm -f "$PYTHON_TO_INSTALL" "$NODEJS_TO_INSTALL"
    echo -e "\n=========================================="
    echo "🎉 包安装完成"
else
    echo -e "\n🎉 没有缺失的包，系统依赖完整"
fi

# 清理所有临时文件
rm -f "$PYTHON_PACKAGES_FILE" "$NODEJS_PACKAGES_FILE"

echo -e "\n=========================================="
echo "=== 所有操作完成 ==="
