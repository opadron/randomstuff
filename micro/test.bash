#! /usr/bin/env bash

curl -d '{"key":"test", "url":""}' -o - 'localhost:8000/register'
curl -d '{"key":"test", "url":""}' -o - 'localhost:8000/subscribe'

curl -d '{"key":"test2", "url":""}' -o - 'localhost:8000/register'
curl -d '{"key":"test2", "url":""}' -o - 'localhost:8000/subscribe'

curl -d '{"key":"test3", "url":""}' -o - 'localhost:8000/register'
curl -d '{"key":"test3", "url":"", "require":[]}' -o - 'localhost:8000/subscribe'

curl -o - 'localhost:8080/hello' ; echo

