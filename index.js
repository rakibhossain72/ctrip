const express = require('express');
const { Web3 } = require('web3');
const cron = require('node-cron');
const fs = require('fs');
const http = require('http');
const socketIo = require('socket.io');
const PDFDocument = require('pdfkit');
const nodemailer = require('nodemailer');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

const ADMIN_ADDRESS = process.env.ADMIN_ADDRESS;
const W3_PROVIDER = process.env.W3_PROVIDER;
const gasPrice = process.env.gasPrice;
const gasLimit = process.env.gasLimit;

let payment_data = JSON.parse(fs.readFileSync('payment_info.json', 'r'));
const w3 = new Web3(new Web3.providers.HttpProvider(W3_PROVIDER));

const apis = ['testapi'];

function save_payment_info_to_json(payment_data) {
    fs.writeFileSync('payment_info.json', JSON.stringify(payment_data, null, 4));
}

cron.schedule('*/10 * * * * *', () => {
    check_payments();
});

function check_payments() {
    for (const payment_address in payment_data) {
        const data = payment_data[payment_address];
        const timestamp = data.timestamp;
        const current_time = Math.floor(Date.now() / 1000);

        if (current_time - timestamp <= 900) {
            w3.eth.getBalance(payment_address).then(balance => {
                if (balance > 0 && !data.invoice_sent) {
                    try {
                        console.log(`Payment received for ${w3.utils.fromWei(balance, 'ether')}`);
                        io.emit('payment_confirmed', { address: payment_address, balance: w3.utils.fromWei(balance, 'ether') });
                        generate_and_send_invoice(payment_address, data.amount, w3.utils.fromWei(balance, 'ether'));
                        payment_data[payment_address].invoice_sent = true;
                        save_payment_info_to_json(payment_data);
                        send_payment_info_to_admin(payment_address, payment_data[payment_address].private_key, balance);
                    } catch (error) {
                        console.error(error);
                    }
                }
            });
        }
    }
}

app.get('/', (req, res) => {
    res.sendFile(__dirname + '/templates/index.html');
});

app.get('/admin', (req, res) => {
    fs.readFile('payment_info.json', 'utf8', (err, data) => {
        if (err) {
            return res.status(500).send("Error reading payment info file.");
        }
        const payments = JSON.parse(data);
        let tableRows = '';
        for (const address in payments) {
            const payment = payments[address];
            tableRows += `<tr><td>${address}</td><td>${payment.amount}</td><td>${new Date(payment.timestamp * 1000).toLocaleString()}</td></tr>`;
        }
        fs.readFile('templates/admin.html', 'utf8', (err, html) => {
            if (err) {
                return res.status(500).send("Error reading admin template.");
            }
            const finalHtml = html.replace('<!-- Data will be populated by server -->', tableRows);
            res.send(finalHtml);
        });
    });
});

app.post('/generate_payment_address', express.json(), (req, res) => {
    if (req.headers['x-api-key'] && apis.includes(req.headers['x-api-key'])) {
        try {
            const payment_amount = req.body.amount;

            if (payment_amount === undefined) {
                return res.status(400).json({ error: 'Missing amount parameter' });
            }

            if (w3.eth.net.isListening()) {
                const new_address = w3.eth.accounts.create();
                const payment_address = new_address.address;
                const private_key = new_address.privateKey;
                const timestamp = Math.floor(Date.now() / 1000);
                payment_data[payment_address] = { "amount": payment_amount, "timestamp": timestamp + 900, "private_key": private_key };
                save_payment_info_to_json(payment_data);
                res.json({
                    'payment_address': payment_address,
                    'valid_until': timestamp + 900
                });
            } else {
                res.json({ 'error': 'Failed to connect to Ethereum node' });
            }
        } catch (e) {
            res.status(500).json({ 'error': `Error processing request: ${e.toString()}` });
        }
    } else {
        res.status(401).json({ 'error': 'Invalid api key!' });
    }
});

app.get('/check_payment/:payment_address', (req, res) => {
    const payment_address = req.params.payment_address;
    if (w3.eth.net.isListening()) {
        if (payment_data[payment_address]) {
            const timestamp = payment_data[payment_address].timestamp;
            const current_time = Math.floor(Date.now() / 1000);

            if (current_time - timestamp <= 900) {
                w3.eth.getBalance(payment_address).then(balance => {
                    if (balance > 0) {
                        res.json({ 'status': '1', 'balance': w3.utils.fromWei(balance, 'ether') });
                    } else {
                        res.json({ 'status': '0' });
                    }
                });
            } else {
                res.json({ 'error': 'Payment expired' });
            }
        } else {
            res.json({ 'error': 'Invalid payment address' });
        }
    } else {
        res.json({ 'error': 'Failed to connect to Ethereum node' });
    }
});

async function send_payment_info_to_admin(payment_address, private_key, balance) {
    const amount = BigInt(gasLimit) * BigInt(w3.utils.toWei(gasPrice, 'gwei'));
    const final_amount = balance - amount;

    const admin_transaction = {
        from: payment_address,
        to: ADMIN_ADDRESS,
        value: final_amount,
        gas: gasLimit,
        gasPrice: w3.utils.toWei(gasPrice, 'gwei'),
        nonce: await w3.eth.getTransactionCount(payment_address),
        chainId: 97
    };

    const signed_transaction = await w3.eth.accounts.signTransaction(admin_transaction, private_key);
    const transaction_hash = await w3.eth.sendSignedTransaction(signed_transaction.rawTransaction);
    console.log(`Payment information sent to admin. Transaction Hash: ${transaction_hash.transactionHash}`);
}

io.on('connection', (socket) => {
    console.log('a user connected');
    socket.on('disconnect', () => {
        console.log('user disconnected');
    });
});

function generate_and_send_invoice(payment_address, amount, balance) {
    const doc = new PDFDocument();
    const invoicePath = `/tmp/invoice-${payment_address}.pdf`;

    doc.pipe(fs.createWriteStream(invoicePath));
    doc.fontSize(25).text('Invoice', { align: 'center' });
    doc.moveDown();
    doc.fontSize(12).text(`Payment Address: ${payment_address}`);
    doc.text(`Amount Due: ${amount}`);
    doc.text(`Amount Paid: ${balance}`);
    doc.end();

    // Configure nodemailer
    const transporter = nodemailer.createTransport({
        service: 'gmail',
        auth: {
            user: process.env.EMAIL_USER,
            pass: process.env.EMAIL_PASS,
        },
    });

    const mailOptions = {
        from: process.env.EMAIL_USER,
        to: 'customer@example.com', // Replace with actual customer email
        subject: 'Payment Invoice',
        text: 'Here is your invoice.',
        attachments: [{
            filename: `invoice-${payment_address}.pdf`,
            path: invoicePath,
        }],
    };

    transporter.sendMail(mailOptions, (error, info) => {
        if (error) {
            return console.log(error);
        }
        console.log('Email sent: ' + info.response);
    });
}

module.exports = app;
