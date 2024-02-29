import { readdirSync, statSync } from "fs";
import { join, extname, basename } from "path";

function getAllFiles(dirPath, filesObject = {}) {
  const files = readdirSync(dirPath);

  files.forEach((file) => {
    if (statSync(join(dirPath, file)).isDirectory()) {
      getAllFiles(join(dirPath, file), filesObject);
    } else {
      const fileName = basename(file, extname(file)); // 去除文件扩展名部分

      filesObject[fileName] = dirPath + "/" + file;
    }
  });

  return filesObject;
}

// 示例用法
const filesObject = getAllFiles("../javascript");
console.log(filesObject);
