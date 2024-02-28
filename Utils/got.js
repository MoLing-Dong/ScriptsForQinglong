/* 
description: This file is used to create a custom instance of got
author: MOL

*/
import got, { Options } from "got";


export default async function (url, method, data) {
  return new Promise((resolve, reject) => {
    try {
      got(url, {
        //   ...options,
        method: method,
        //   body: data,
      }).then(
        (res) => {
          // console.log(res.body);
          resolve(res.body);
        },
        (err) => {
          console.log(err);
          reject(err);
        }
      );
    } catch (error) {
      reject(error);
    }
  });
}
