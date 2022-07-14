
const { createServer } = require("http");
const express = require("express");
const crypto = require("crypto");
const url = require("url");
const http = require("http");

const isNil = (x) => (x === (void 0) || x === null);

const readJson = (readable) => new Promise((resolve, reject) => {
  let body = [];
  const addChunk = (chunk) => body.push(chunk);
  const parseJson = () => {
    try {
      resolve(body.length ? JSON.parse(body.join("")) : {});
    } catch (err) {
      reject(err);

      readable.removeListener("data", addChunk);
      readable.removeListener("end", parseJson);
    }
  };

  readable.setEncoding("utf8");
  readable.on("data", addChunk);
  readable.on("end", parseJson);
});

const jsonAPI = (func) => async (req, res) => {
  let body, message, status;

  try {
    let data = await func(await readJson(req));
    ({ status = 200, message, body } = (data || {}));
  } catch (err) {
    console.log(`API Error ${err}`);
    ({ status = 400, message } = err);
  }

  res.status(status);

  if (body) {
    res.json(body);
  } else if (message) {
    res.send(message);
  }

  res.end();
};

const requiredParameters = (params, predicate = isNil) => {
  const missingParameters = (
    Object.entries(params)
      .filter(([k, v]) => predicate(v))
      .map(([k]) => k)
  );

  if (missingParameters.length) {
    let s = (missingParameters.length === 1 ? "" : "s");
    let p = missingParameters.map(JSON.stringify).join(", ");

    let error = new Error(`missing parameter${s}: ${p}`);

    throw error;
  }
};

class Subscriptions {
  constructor() {
    this.table = new Map();
    this.routerPromise = null;
    this.counter = new Uint32Array(1);
    this.inFlightObjects = {};
  }

  async addFlightObject({ method, path }) {
    const count = this.counter[0]++;
    method = method.toLowerCase();

    const hasher = crypto.createHash("sha256");
    hasher.update(count.toString());
    hasher.update(method);
    hasher.update(path);
    const hash = hasher.digest("hex");

    this.inFlightObjects[hash] = { path };

    return hash;
  }

  getRequest(hash) {
    if (hash in this.inFlightObjects) {
      return (this.inFlightObjects[hash].request || {}).body || "";
    }
  }

  getRequestHeaders(hash) {
    if (hash in this.inFlightObjects) {
      return (this.inFlightObjects[hash].request || {}).headers || {};
    }
  }

  setRequest(hash, res) {
    if (hash in this.inFlightObjects) {
      this.inFlightObjects[hash].request =
        (this.inFlightObjects[hash].request || {});

      this.inFlightObjects[hash].request.body = res;
    }
  }

  setRequestHeaders(hash, res, headers) {
    if (hash in this.inFlightObjects) {
      this.inFlightObjects[hash].request =
        (this.inFlightObjects[hash].request || {});

      this.inFlightObjects[hash].request.headers = {
        ...(this.inFlightObjects[hash].request.headers || {}),
        ...headers
      };
    }
  }

  getResponse(hash) {
    if (hash in this.inFlightObjects) {
      return (this.inFlightObjects[hash].response || {}).body || "";
    }
  }

  getResponseHeaders(hash) {
    if (hash in this.inFlightObjects) {
      return (this.inFlightObjects[hash].response || {}).headers || {};
    }
  }

  setResponse(hash, res) {
    if (hash in this.inFlightObjects) {
      this.inFlightObjects[hash].response =
        (this.inFlightObjects[hash].response || {});

      this.inFlightObjects[hash].response.body = res;
    }
  }

  setResponseHeaders(hash, res, headers) {
    if (hash in this.inFlightObjects) {
      this.inFlightObjects[hash].response =
        (this.inFlightObjects[hash].response || {});

      this.inFlightObjects[hash].response.headers = {
        ...(this.inFlightObjects[hash].response.headers || {}),
        ...headers
      };
    }
  }

  hasFlightObject(hash) {
    return hash in this.inFlightObjects;
  }

  addRoute({ method, path, key, require }) {
    method = method.toLowerCase();

    const hasher = crypto.createHash("sha256");
    hasher.update(method);
    hasher.update(path);
    hasher.update(key);
    const hash = hasher.digest("hex");

    this.table[hash] = {
      hash, method, path, key, require
    };

    this.routerPromise = null;
  }

  async getRouter() {
    return this.routerPromise = (
      isNil(this.routerPromise)
      ? (
        Promise.resolve(express.Router())
          .then((router) => {
            let counter = 0;

            router.all("*", async (req, res, next) => {
              const hash = await this.addFlightObject({
                method: req.method,
                path: url.parse(req.url).path
              });

              req.flightHash = hash;

              next();
            });

            Object.values(this.table).forEach(
              ({ method, path, key, ...data}) => {
                router[method](path, ((method, path, key, data) => (req, res, next) => 
                  {
                    let visitedMap = req.visitedMap || {};
                    let dataMap = req.dataMap || {};

                    visitedMap[key] = true;
                    req.visitedMap = visitedMap;

                    dataMap[key] = data;
                    req.dataMap = dataMap;

                    next();
                  }
                )(method, path, key, data));
              }
            );

            router.all("*", async (req, res, next) => {
              let visitedMap = req.visitedMap;
              if (!visitedMap) {
                next();
                return;
              }

              let dataMap = req.dataMap;
              let processedMap = {};

              let todo = Object.keys(visitedMap);
              while (todo.length) {
                let key = todo.pop();
                console.log(`Checking ${key}`);

                if (processedMap[key]) {
                  continue;
                }

                let requirements = ((dataMap[key] || {}).require || []);
                requirements = requirements.filter((r) => !processedMap[r]);

                if (requirements.length) {
                  todo.push(key);
                  requirements.forEach((r) => todo.push(r));
                  continue;
                }

                console.log(Boolean(visitedMap[key]));

                if (visitedMap[key]) {
                  let urlStr = clients[key].url;
                  if (urlStr.endsWith("/")) {
                    urlStr = urlStr.substring(0, urlStr.length - 1);
                  }

                  urlStr += this.inFlightObjects[req.flightHash].path;

                  console.log(`Calling sub server: ${urlStr}`);

                  let urlObj = new url.URL(urlStr);
                  let reqOptions = {
                    hostname: urlObj.hostname,
                    port: urlObj.port,
                    path: urlObj.pathname,
                    method: "POST",
                    headers: {
                      "Content-Type": "application/x-www-form-urlencoded",
                      "Content-Length": 0,
                      "x-micro-id": req.flightHash
                    }
                  };

                  await new Promise((resolve, reject) => {
                    let req = http.request(reqOptions, (res) => {
                      res.on("data", (chunk) => {});
                      res.on("end", resolve);
                    });

                    req.on("error", reject);
                    req.end();
                  });

                  // res.write(`Peer handled: ${key} (${req.flightHash}).\n`);
                }

                processedMap[key] = true;
              }

              console.log("Setting response headers");
              Object.entries(this.getResponseHeaders(req.flightHash))
                .forEach(([k, v]) => {
                  console.log(`Setting response header: ${k} | ${v}`);
                  res.setHeader(k, v);
                });

              /* TODO: add routes for response status */
              res.status(200);

              // let body = this.getResponse(req.flightHash);
              // console.log(`Sending response body: [${body}]`);
              res.send(this.getResponse(req.flightHash));
              res.end();
            });

            return router;
          })
      )

      : this.routerPromise
    );
  }

};

let clients = {};
let subscriptions = new Subscriptions();

const registrationApp = express();
const apiApp = express();

registrationApp.post("/register", jsonAPI(async ({ key, url }) => {
  requiredParameters({ key, url });

  let entry = clients[key] || {};
  entry.url = url;
  entry.count = (entry.count || 0) + 1;

  console.log("REGISTRATION");
  console.log(entry);

  clients[key] = entry;

  return {};
}));

registrationApp.post("/subscribe", jsonAPI(async ({
  method = "GET",
  path = "*",
  require = [],
  key
}) => {
  requiredParameters({ key });
  subscriptions.addRoute({ method, path, require, key });
}));

registrationApp.get("/table", jsonAPI(async () => ({ body: {
  subscriptions: subscriptions.table, clients
} })));

// registrationApp.post("/test", (req, res) => {
//   res.write(JSON.stringify(req.headers), () =>
//     res.write("\n", () => req.pipe(res))
//   );
// 
//   // req.on("data", (x) => res.write(x));
//   // req.on("end", () => res.end());
//   // res.end(JSON.stringify(req.headers));
// });

registrationApp.get("/request/:hash/headers", async (req, res) => {
  const { hash } = req.params;
  if (!subscriptions.hasFlightObject(hash)) {
    res.status(400).end();
    return;
  }

  res.json(subscriptions.getRequestHeaders()).end();
});

registrationApp.put("/request/:hash/headers", async (req, res) => {
  const { hash } = req.params;
  if (!subscriptions.hasFlightObject(hash)) {
    res.status(400).end();
    return;
  }
  subscriptions.setRequestHeaders(await readJson(req));
  res.status(200).end();
});

registrationApp.get("/request/:hash/body", async (req, res) => {
  const { hash } = req.params;
  if (!subscriptions.hasFlightObject(hash)) {
    res.status(400).end();
    return;
  }

  return subscriptions.getRequest(hash);
});

registrationApp.put("/request/:hash/body", async (req, res) => {
  const { hash } = req.params;
  if (!subscriptions.hasFlightObject(hash)) {
    res.status(400).end();
    return;
  }

  let body = [];
  const onData = (chunk) => body.push(chunk);

  const onEnd = () => {
    subscriptions.setRequest(hash, body.join(""));
    req.removeListener("data", onData);
    req.removeListener("end", onEnd);

    res.status(200).end();
  };

  req.setEncoding("utf8");
  req.on("data", onData);
  req.on("end", onEnd);
});

registrationApp.get("/response/:hash/headers", async (req, res) => {
  const { hash } = req.params;
  if (!subscriptions.hasFlightObject(hash)) {
    res.status(400).end();
    return;
  }

  res.json(subscriptions.getResponseHeaders()).end();
});

registrationApp.put("/response/:hash/headers", async (req, res) => {
  const { hash } = req.params;
  if (!subscriptions.hasFlightObject(hash)) {
    res.status(400).end();
    return;
  }
  subscriptions.setResponseHeaders(await readJson(req));
  res.status(200).end();
});

registrationApp.get("/response/:hash/body", async (req, res) => {
  const { hash } = req.params;
  if (!subscriptions.hasFlightObject(hash)) {
    res.status(400).end();
    return;
  }

  return subscriptions.getResponse(hash);
});

registrationApp.put("/response/:hash/body", async (req, res) => {
  const { hash } = req.params;
  if (!subscriptions.hasFlightObject(hash)) {
    res.status(400).end();
    return;
  }

  let body = [];
  const onData = (chunk) => body.push(chunk);

  const onEnd = () => {
    subscriptions.setResponse(hash, body.join(""));
    console.log(`Response set: ${hash}`);
    console.log(subscriptions.getResponse(hash));
    req.removeListener("data", onData);
    req.removeListener("end", onEnd);

    res.status(200).end();
  };

  req.setEncoding("utf8");
  req.on("data", onData);
  req.on("end", onEnd);
});

apiApp.all("*", async (req, res, next) =>
  (await subscriptions.getRouter())(req, res, next));

registrationApp.listen(8000, () => {
  apiApp.listen(8080, () => {});
});

