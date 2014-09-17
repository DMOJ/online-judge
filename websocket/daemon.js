var config = require('./config');
var set = require('simplesets').Set;
var queue = require('qu');
var WebSocketServer = require('ws').Server;
var wss_receiver = new WebSocketServer({host: config.get_host, port: config.get_port});
var wss_sender = new WebSocketServer({host: config.post_host, port: config.post_port});
var messages = new queue();
var followers = new set();
var pollers = new set();
var max_queue = config.max_queue || 50;
var message_id = Date.now();

if (typeof String.prototype.startsWith != 'function') {
    String.prototype.startsWith = function (str){
        return this.slice(0, str.length) == str;
    };
}

messages.catch_up = function (client) {
    this.each(function (message) {
        if (message.id > client.last_msg)
            client.got_message(message);
    });
};

messages.post = function (channel, message) {
    message = {
        id: ++message_id,
        channel: channel,
        message: message
    };
    this.push(message);
    if (this.length > max_queue)
        this.shift();
    followers.each(function (client) {
        client.got_message(message);
    });
    pollers.each(function (request) {
        request.got_message(message);
    });
    return message.id;
};

messages.last = function () {
    return this.tail().id;
};

wss_receiver.on('connection', function (socket) {
    socket.channel = null;
    socket.last_msg = 0;

    var commands = {
        start_msg: function (request) {
            socket.last_msg = request.start;
        },
        set_filter: function (request) {
            var filter = {};
            if (Array.isArray(request.filter) && request.filter.every(function (channel, index, array) {
                if (typeof channel != 'string')
                    return false;
                filter[channel] = true;
                return true;
            })) {
                socket.filter = request.filter.length == 0 ? true : filter;
                followers.add(socket);
                messages.catch_up(socket);
            } else {
                socket.send(JSON.stringify({
                    status: 'error',
                    code: 'invalid-filter',
                    message: 'invalid filter: ' + request.filter
                }));
            }
        },
    };

    socket.got_message = function (message) {
        if (socket.filter === true || message.channel in socket.filter)
            socket.send(JSON.stringify(message));
        socket.last_msg = message.id;
    };

    socket.on('message', function (request) {
        try {
            request = JSON.parse(request);
        } catch (err) {
            socket.send(JSON.stringify({
                status: 'error',
                code: 'syntax-error',
                message: err.message
            }));
            return;
        }
        request.command = request.command.replace(/-/g, '_');
        if (request.command in commands)
            commands[request.command](request);
        else
            socket.send(JSON.stringify({
                status: 'error',
                code: 'bad-command',
                message: 'bad command: ' + request.command
            }));
    });

    socket.on('close', function(code, message) {
        followers.remove(socket);
    });
});

wss_sender.on('connection', function (socket) {
    var commands = {
        post: function (request) {
            if (typeof request.channel != 'string')
                return {
                    status: 'error',
                    code: 'invalid-channel'
                };
            return {
                status: 'success',
                id: messages.post(request.channel, request.message)
            };
        },
        last_msg: function (request) {
            return {
                status: 'success',
                id: message_id,
            };
        }
    };
    socket.on('message', function (request) {
        try {
            request = JSON.parse(request);
        } catch (err) {
            socket.send(JSON.stringify({
                status: 'error',
                code: 'syntax-error',
                message: err.message
            }));
            return;
        }
        request.command = request.command.replace(/-/g, '_');
        if (request.command in commands)
            socket.send(JSON.stringify(commands[request.command](request)));
        else
            socket.send(JSON.stringify({
                status: 'error',
                code: 'bad-command',
                message: 'bad command: ' + request.command
            }));
    });
});

var url = require('url');
require('http').createServer(function (req, res) {
    var parts = url.parse(req.url, true);

    if (!parts.pathname.startsWith('/channels/')) {
        res.writeHead(404, {'Content-Type': 'text/plain'});
        res.end('404 Not Found');
    }
    var channels = parts.pathname.slice(10).split('|');
    req.channels = {};
    req.last_msg = parseInt(parts.query.last);
    if (isNaN(req.last_msg)) req.last_msg = 0;

    console.log(channels);
    if (!channels.every(function (channel, index, array) {
        if (!channel || !channel.length)
            return false;
        return req.channels[channel] = true;
    })) req.channels = true;
    console.log(req.channels);

    req.on('close', function () {
        pollers.remove(req);
    });

    req.got_message = function (message) {
        if (req.channels === true || message.channel in req.channels) {
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(message));
            pollers.remove(req);
            return true;
        }
        return false;
    };
    var got = false;
    messages.each(function (message) {
        if (!got && message.id > req.last_msg)
            got = req.got_message(message);
    });
    if (!got) pollers.add(req);
}).listen(config.http_port, config.http_host);