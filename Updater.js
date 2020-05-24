const client = require('dgram').createSocket('udp4');
a = {"C:/GitHub/DC/Client/License.key": [1,2,4]}

const message = Buffer.from(JSON.stringify(a));

client.send(message, 33456, 'localhost', (err) => {
  client.close();
});