import path from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

console.log(path.resolve(dirname(fileURLToPath(import.meta.url)), "dist"));
