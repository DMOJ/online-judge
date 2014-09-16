var set = require('simplesets').Set;
var queue = require('qu');
var WebSocketServer = require('ws').Server;
var wss_receiver = new WebSocketServer({port: 17001});
var wss_sender = new WebSocketServer({port: 17002});
var channels = {};
var max_channel = 10;
var message_id = Date.now();

wss_receiver.on('connection', function (socket) {
    socket.channel = null;
    socket.last_msg = null;

    var commands = {
        start_msg: function (request) {
            socket.last_msg = request.start;
        },
        set_channel: function (request) {
            if (request.channel in channels) {
                if (socket.channel != null)
                    socket.channel.followers.remove(socket);
                socket.channel = channels[request.channel];
                socket.channel.followers.add(socket);
                socket.send(JSON.stringify({
                    status: 'success',
                    message: 'channel set to ' + request.channel
                }));
                socket.channel.catch_up(socket);
            } else
                socket.send(JSON.stringify({
                    status: 'error',
                    code: 'no-channel',
                    message: 'channel no exist: ' + request.channel
                }));
        },
    };

    socket.got_message = function (message) {
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
        if (socket.channel != null)
            socket.channel.followers.remove(socket);
    });
});

wss_sender.on('connection', function (socket) {
    var commands = {
        new_channel: function (request) {
            if (request.channel in channels) {
                socket.send(JSON.stringify({
                    status: 'error',
                    code: 'channel-exists',
                    message: 'channel exists: ' + request.channel
                }));
                return;
            }
            channels[request.channel] = {
                messages: new queue(),
                followers: new set(),
                catch_up: function (client) {
                    this.messages.each(function (message) {
                        if (message.id > client.last_msg)
                            client.got_message(message);
                    });
                },
                add: function (message) {
                    message = {
                        id: message_id++,
                        message: message
                    };
                    this.messages.push(message);
                    if (this.messages.length > max_channel)
                        this.messages.shift();
                    this.followers.each(function (client) {
                        client.got_message(message);
                    });
                    return message.id;
                },
                last: function () {
                    return this.messages.tail().id;
                }
            };
            socket.send(JSON.stringify({
                status: 'success'
            }));
        },
        post: function (request) {
            if (request.channel in channels) {
                socket.send(JSON.stringify({
                    status: 'success',
                    id: channels[request.channel].add(request.message)
                }));
            } else
                socket.send(JSON.stringify({
                    status: 'error',
                    code: 'no-channel'
                }));
        },
        last_msg: function (request) {
            if (request.channel in channels) {
                socket.send(JSON.stringify({
                    status: 'success',
                    id: channels[request.channel].last()
                }));
            } else
                socket.send(JSON.stringify({
                    status: 'error',
                    code: 'no-channel'
                }));
        }
    };
    socket.on('message', function (request) {
        request = JSON.parse(request);
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
});