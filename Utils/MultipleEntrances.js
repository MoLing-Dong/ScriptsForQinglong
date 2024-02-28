import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

export function getAllFiles(dirPath, arrayOfFiles = []) {
  const files = readdirSync(dirPath);

  files.forEach((file) => {
    if (statSync(join(dirPath, file)).isDirectory()) {
      getAllFiles(join(dirPath, file), arrayOfFiles);
    } else {
      arrayOfFiles.push(join(dirPath, file));
    }
  });

  return arrayOfFiles;
}

// 生成八位随机 hash
const randomHash = () => Math.random().toString(36).substr(2, 8);

// 格式化为 {key:value} 格式
export function objFormat(dirPath) {
  return getAllFiles(dirPath).reduce(
    (obj, item) => ({ ...obj, [randomHash()]: item }),
    {}
  );
}
