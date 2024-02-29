import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

export function getAllFiles(dirPath, filesObject = {}) {
  const files = readdirSync(dirPath);

  files.forEach((file) => {
    if (statSync(join(dirPath, file)).isDirectory()) {
      getAllFiles(join(dirPath, file), filesObject);
    } else {
      filesObject[file] = dirPath + "/" + file;
    }
  });

  return filesObject;
}
