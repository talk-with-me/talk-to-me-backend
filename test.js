/**
 * test.js - testing script for talk-to-me backend
 */

const socket = require('socket.io-client')('http://localhost:8000');
const fetch = require('node-fetch');
const baseUrl = 'http://localhost:8000';
let socket = null;

let users = [];

function addUser(user) {
  users.push(user);
  console.log(user);
}

test('request to auth should return user info', done => {
  fetch(baseUrl+'/auth', { method : 'GET' })
    .then(response => {
      expect(response.status).toEqual(200);
      response.json().then(json => {
        addUser(json); 
        done();
      });
    });
});

test('queue should return 200', done => {
  console.log(users[0]['data']['secret']);
  fetch(baseUrl+'/queue', { 
    method : 'POST' , 
    body : JSON.stringify({ 'secret' : users[0]['data']['secret']}),
    headers: { 'Content-Type': 'application/json' }
  })
    .then(response => {
      expect(response.status).toEqual(200);
      done();
    });
});

