/* 
@description: 获取指定目录下的所有文件
@author:MOL
@params: dirPath: string, filesObject: object(可选)
@return: object{fileName: filePath}
 */
import { readdirSync, statSync } from "node:fs";
import { join, extname, basename } from "node:path";

export function getAllFiles(dirPath, filesObject = {}) {
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
