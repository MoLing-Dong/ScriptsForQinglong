import { readdirSync, statSync } from "fs";
import { join } from "path";

function getAllFiles(dirPath, filesObject = {}) {
  const files = readdirSync(dirPath);

  files.forEach((file) => {
    if (statSync(join(dirPath, file)).isDirectory()) {
      getAllFiles(join(dirPath, file), filesObject);
    } else {
      filesObject[file] = dirPath+'/'+file;
    }
  });

  return filesObject;
}

// 示例用法
const filesObject = getAllFiles("../javascript");
console.log(filesObject);
