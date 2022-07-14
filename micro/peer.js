
const { createServer } = require("http");
const express = require("express");

const http = require("http");
const url = require("url");

const app = express();

const apiUrl = "http://localhost:8000";

app.post("/hello", async (req, res) => {
  const id = req.headers["x-micro-id"];
  const urlStr = `${apiUrl}/response/${id}/body`;
  const urlObj = new url.URL(urlStr);
  const body = "Hello, World!";
  const reqOptions = {
    hostname: urlObj.hostname,
    port: urlObj.port,
    path: urlObj.pathname,
    method: "PUT",
    headers: {
      "Content-Type": "text/plain",
      "Content-Length": Buffer.byteLength(body)
    }
  };

  await new Promise((resolve, reject) => {
    let req = http.request(reqOptions, (res) => {
      res.on("data", (chunk) => {});
      res.on("end", resolve);
    });

    req.on("error", reject);
    req.write(body, () => req.end());
  });

  console.log("Hello, World!");
  console.log(req.headers);
  res.end();
});

new Promise((resolve, reject) => {
  let urlObj = new url.URL(`${apiUrl}/register`);
  let data = JSON.stringify({ key: "test", url: "http://localhost:9000" });
  let reqOptions = {
    hostname: urlObj.hostname,
    port: urlObj.port,
    path: urlObj.pathname,
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "Content-Length": Buffer.byteLength(data)
    }
  };

  let req = http.request(reqOptions, (res) => {
    res.on("data", (chunk) => console.log(`DATA: ${chunk}`));
    res.on("end", resolve);
  });

  req.on("error", reject);
  req.write(data, () => req.end());
})

.then(() => new Promise((resolve, reject) => {
  let urlObj = new url.URL(`${apiUrl}/subscribe`);
  let data = JSON.stringify({ method: "GET", path: "/hello", key: "test" });

  let reqOptions = {
    hostname: urlObj.hostname,
    port: urlObj.port,
    path: urlObj.pathname,
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "Content-Length": Buffer.byteLength(data)
    }
  };

  let req = http.request(reqOptions, (res) => {
    res.on("data", (chunk) => console.log(`DATA: ${chunk}`));
    res.on("end", resolve);
  });

  req.on("error", reject);
  req.write(data, () => req.end());
}))

.catch((err) => { console.log(`ERROR: ${err}`); });

app.listen(9000, () => { console.log("READY"); });

