#!/bin/bash

# 检测青龙面板日志中缺失的Python和Node.js包（容器内运行版本）
echo "=== 检测缺失的依赖包 ==="
echo "扫描近7天的日志文件..."

# 创建临时文件存储结果
PYTHON_PACKAGES_FILE="/tmp/python_packages.txt"
NODEJS_PACKAGES_FILE="/tmp/nodejs_packages.txt"

# 清空临时文件
> "$PYTHON_PACKAGES_FILE"
> "$NODEJS_PACKAGES_FILE"

echo "=== Python包检测（近7天日志） ==="
echo "查找包含ModuleNotFoundError的日志文件:"
find /ql -name '*.log' -type f -mtime -7 -exec grep -l 'ModuleNotFoundError\|No module named' {} \; 2>/dev/null

echo
echo "提取缺失的Python包名:"
find /ql -name '*.log' -type f -mtime -7 -exec grep -h 'ModuleNotFoundError\|No module named' {} \; 2>/dev/null | \
sed -n "s/.*No module named '\([^']*\)'.*/\1/p; s/.*ModuleNotFoundError: No module named \([^ ]*\).*/\1/p" | \
sort | uniq | tee "$PYTHON_PACKAGES_FILE"

echo
echo "=== Node.js包检测（近7天日志） ==="
echo "查找包含Node.js模块错误的日志文件:"
find /ql -name '*.log' -type f -mtime -7 -exec grep -l "Cannot find module\|MODULE_NOT_FOUND\|Error: Cannot resolve module" {} \; 2>/dev/null

echo
echo "提取缺失的Node.js包名:"
find /ql -name '*.log' -type f -mtime -7 -exec grep -h "Cannot find module\|MODULE_NOT_FOUND\|Error: Cannot resolve module" {} \; 2>/dev/null | \
sed -n "s/.*Cannot find module '\([^']*\)'.*/\1/p; s/.*Cannot find module \"\([^\"]*\)\".*/\1/p; s/.*MODULE_NOT_FOUND.*'\([^']*\)'.*/\1/p; s/.*Error: Cannot resolve module '\([^']*\)'.*/\1/p" | \
grep -v "^/" | grep -v "^\." | \
sort | uniq | tee "$NODEJS_PACKAGES_FILE"

echo
echo "=========================================="
echo "=== 检测结果汇总 ==="

# 显示Python包结果
if [ -s "$PYTHON_PACKAGES_FILE" ]; then
    echo
    echo "=== 缺失的Python包 ==="
    cat "$PYTHON_PACKAGES_FILE"
    
    echo
    echo "Python包安装命令："
    echo "逐个安装："
    while IFS= read -r package; do
        echo "  pip3 install $package"
    done < "$PYTHON_PACKAGES_FILE"
    echo
    echo "一次性安装："
    echo -n "  pip3 install "
    tr '\n' ' ' < "$PYTHON_PACKAGES_FILE"
    echo
else
    echo "✓ 未发现缺失的Python包"
fi

# 显示Node.js包结果
if [ -s "$NODEJS_PACKAGES_FILE" ]; then
    echo
    echo "=== 缺失的Node.js包 ==="
    cat "$NODEJS_PACKAGES_FILE"
    
    echo
    echo "Node.js包安装命令："
    echo "使用npm安装："
    while IFS= read -r package; do
        echo "  npm install $package"
    done < "$NODEJS_PACKAGES_FILE"
    echo
    echo "一次性安装："
    echo -n "  npm install "
    tr '\n' ' ' < "$NODEJS_PACKAGES_FILE"
    echo
    echo
    echo "使用pnpm安装（推荐）："
    while IFS= read -r package; do
        echo "  pnpm install $package"
    done < "$NODEJS_PACKAGES_FILE"
    echo
    echo "一次性安装："
    echo -n "  pnpm install "
    tr '\n' ' ' < "$NODEJS_PACKAGES_FILE"
    echo
else
    echo "✓ 未发现缺失的Node.js包"
fi

# 验证并安装缺失的包
if [ -s "$PYTHON_PACKAGES_FILE" ] || [ -s "$NODEJS_PACKAGES_FILE" ]; then
    echo
    echo "=========================================="
    echo "=== 验证包安装状态 ==="
    
    # 创建需要安装的包列表
    PYTHON_TO_INSTALL="/tmp/python_to_install.txt"
    NODEJS_TO_INSTALL="/tmp/nodejs_to_install.txt"
    > "$PYTHON_TO_INSTALL"
    > "$NODEJS_TO_INSTALL"
    
    if [ -s "$PYTHON_PACKAGES_FILE" ]; then
        echo "检查Python包安装状态..."
        while IFS= read -r package; do
            if python3 -c "import $package" 2>/dev/null; then
                echo "✓ $package 已安装"
            else
                echo "✗ $package 需要安装"
                echo "$package" >> "$PYTHON_TO_INSTALL"
            fi
        done < "$PYTHON_PACKAGES_FILE"
    fi
    
    if [ -s "$NODEJS_PACKAGES_FILE" ]; then
        echo "检查Node.js包安装状态..."
        while IFS= read -r package; do
            if node -e "require('$package')" 2>/dev/null; then
                echo "✓ $package 已安装"
            else
                echo "✗ $package 需要安装"
                echo "$package" >> "$NODEJS_TO_INSTALL"
            fi
        done < "$NODEJS_PACKAGES_FILE"
    fi
    
    echo
    echo "=========================================="
    echo "=== 开始安装缺失的包 ==="
    
    if [ -s "$PYTHON_TO_INSTALL" ]; then
        echo "开始安装Python包..."
        while IFS= read -r package; do
            echo "正在安装 $package..."
            pip3 install "$package"
        done < "$PYTHON_TO_INSTALL"
        echo "✓ Python包安装完成！"
    else
        echo "✓ 所有Python包都已安装"
    fi
    
    if [ -s "$NODEJS_TO_INSTALL" ]; then
        echo "开始使用pnpm安装Node.js包..."
        while IFS= read -r package; do
            echo "正在安装 $package..."
            pnpm install "$package"
        done < "$NODEJS_TO_INSTALL"
        echo "✓ Node.js包安装完成！"
    else
        echo "✓ 所有Node.js包都已安装"
    fi
    
    # 清理临时文件
    rm -f "$PYTHON_TO_INSTALL" "$NODEJS_TO_INSTALL"
    
    echo "=========================================="
    echo "🎉 包安装验证和补充完成！"
else
    echo
    echo "🎉 没有发现缺失的包，系统依赖完整！"
fi

# 清理临时文件
rm -f "$PYTHON_PACKAGES_FILE" "$NODEJS_PACKAGES_FILE"

echo
echo "=========================================="
echo "=== 检测完成 ==="
